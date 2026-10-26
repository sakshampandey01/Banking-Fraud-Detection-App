"""Start-up state of the ML side of the application, with no web or database imports.

Why this exists: the original start-up crashed with a stack trace when the model file, the
preprocessing values or the database were not ready. Now the server always starts, /api/health says
exactly what is missing, and scoring endpoints answer 503 with the same instructions - while the
dashboard keeps working for everything that does not need the model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.ml.features import FeatureBuilder, PreprocessingNotReady
from app.ml.model_service import FraudModel, ModelUnavailable


@dataclass(frozen=True)
class Issue:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class DatabaseProblem(Exception):
    """Raised by the database layer with a user-readable explanation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class ScoringUnavailable(RuntimeError):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__(" | ".join(i.message for i in issues))


@dataclass
class Runtime:
    preprocessing_path: Path
    model_path: Path
    model: FraudModel | None = None
    builder: FeatureBuilder | None = None
    artifact_issues: list[Issue] = field(default_factory=list)
    db_issue: Issue | None = None
    db_checked: bool = False          # True once the database encoding has been compared successfully

    # ------------------------------------------------------------------ loading
    def load_artifacts(self) -> None:
        self.artifact_issues.clear()
        self.model = self.builder = None
        try:
            self.builder = FeatureBuilder.from_file(self.preprocessing_path)
        except PreprocessingNotReady as exc:
            self.artifact_issues.append(Issue("PREPROCESSING_NOT_READY", str(exc)))
        try:
            self.model = FraudModel.load(self.model_path)
        except ModelUnavailable as exc:
            self.artifact_issues.append(Issue("MODEL_UNAVAILABLE", str(exc)))

        if self.model and self.builder and self.model.features != self.builder.features:
            self.artifact_issues.append(Issue(
                "FEATURE_MISMATCH",
                f"The model expects features {self.model.features} but preprocessing.json provides "
                f"{self.builder.features}. Predictions would be wrong, so scoring is disabled."))

    # ------------------------------------------------------- database consistency
    def verify_database(self, fetch_type_encoding: Callable[[], dict[str, int]]) -> None:
        """Compare the database's transaction_types with the model's encoding. Retried until it succeeds."""
        try:
            db_enc = fetch_type_encoding()
        except DatabaseProblem as exc:
            self.db_issue, self.db_checked = Issue(exc.code, exc.message), False
            return
        except Exception as exc:  # never let a health check crash the server
            self.db_issue, self.db_checked = Issue("DB_ERROR", f"{type(exc).__name__}: {exc}"), False
            return

        if self.builder is not None and db_enc != self.builder.type_encoding:
            self.db_issue = Issue(
                "DB_ENCODING_MISMATCH",
                f"transaction_types in the database {db_enc} differs from the model's encoding "
                f"{self.builder.type_encoding}. Run `python scripts/init_db.py` to re-seed it.")
            self.db_checked = False
            return
        self.db_issue, self.db_checked = None, True

    # ----------------------------------------------------------------- readiness
    def model_issues(self) -> list[Issue]:
        return list(self.artifact_issues)

    def scoring_issues(self) -> list[Issue]:
        return self.model_issues() + ([self.db_issue] if self.db_issue else [])

    def require_model(self) -> tuple[FraudModel, FeatureBuilder]:
        """For stateless scoring (no database involved)."""
        issues = self.model_issues()
        if issues or self.model is None or self.builder is None:
            raise ScoringUnavailable(issues or [Issue("MODEL_UNAVAILABLE", "Model is not loaded.")])
        return self.model, self.builder

    def require_scoring(self, fetch_type_encoding: Callable[[], dict[str, int]]) -> tuple[FraudModel, FeatureBuilder]:
        """For evaluate: artifacts must be loaded AND the database encoding must agree with them."""
        model, builder = self.require_model()          # raises first if artifacts are missing
        if not self.db_checked:
            self.verify_database(fetch_type_encoding)
        if self.db_issue:
            raise ScoringUnavailable([self.db_issue])
        return model, builder
