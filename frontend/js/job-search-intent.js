// Keep a visitor's job search through sign-in without changing access rules.
var pending = null;
const key = 'kf_job_search';

function rememberJobSearch(query, city){
  pending = { query:String(query || '').trim().slice(0,120), city:String(city || '').trim().slice(0,80) };
  try { sessionStorage.setItem(key, JSON.stringify(pending)); } catch(e) {}
}

function peekJobSearch(){
  if (pending) return pending;
  try {
    var saved = JSON.parse(sessionStorage.getItem(key));
    if (saved && typeof saved.query === 'string' && typeof saved.city === 'string') return saved;
  } catch(e) {}
  return null;
}

function consumeJobSearch(){
  var saved = peekJobSearch();
  pending = null;
  try { sessionStorage.removeItem(key); } catch(e) {}
  return saved;
}

function authDestination(){ return peekJobSearch() ? '#/jobs' : '#/'; }

export { rememberJobSearch, peekJobSearch, consumeJobSearch, authDestination };
