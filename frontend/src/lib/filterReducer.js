import { VIEWS } from './constants.js';

export const initialFilterState = { view: VIEWS.ALL, query: '' };

/** Pure reducer (no React import) so it can be unit-tested with plain Node. */
export function filterReducer(state, action) {
  switch (action.type) {
    case 'SET_VIEW':  return { ...state, view: action.view };
    case 'SET_QUERY': return { ...state, query: action.query };
    case 'RESET':     return initialFilterState;
    default:          return state;
  }
}
