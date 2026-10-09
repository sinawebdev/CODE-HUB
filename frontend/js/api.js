// Same-origin HTTP API. Successful calls retain the demo's {data, message} envelope.
export const API_BASE = (document.querySelector('meta[name="api-base"]')?.content || '/api/v1').replace(/\/$/, '');
const read = key => { try { return localStorage.getItem(key) || ''; } catch { return ''; } };
const store = (key, value) => { try { if(value)localStorage.setItem(key,value);else localStorage.removeItem(key); } catch {} };
export function setTokens(access, refresh){store('kf_access',access);store('kf_refresh',refresh);store('kf_token','');}
export function clearTokens(){store('kf_access','');store('kf_refresh','');store('kf_token','');}
export function hasSession(){return !!(read('kf_access') || read('kf_refresh'));}
let refreshing = null;
function errorFor(data,status){const e=new Error(data.detail || 'Something went wrong. Please try again.');e.code=data.code;e.status=status;return e;}
async function refreshSession(){
  if(!refreshing)refreshing=(async()=>{
    try {
      const response=await fetch(API_BASE+'/auth/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refreshToken:read('kf_refresh')})});
      const data=await response.json();
      if(!response.ok || !data.data?.accessToken)throw new Error('Refresh failed');
      setTokens(data.data.accessToken,data.data.refreshToken);
    } catch {
      clearTokens();window.dispatchEvent(new Event('kf:signed-out'));
      throw errorFor({detail:'Please sign in again.',code:'AUTH_REQUIRED'},401);
    } finally {refreshing=null;}
  })();
  return refreshing;
}
export async function request(method,path,{query,body,form}={},retry=true){
  const url=new URL(API_BASE+path,location.origin);
  for(const [key,value]of Object.entries(query || {}))if(value!==undefined && value!==null && value!=='')url.searchParams.set(key,String(value));
  const headers={}, access=read('kf_access');
  if(access)headers.Authorization='Bearer '+access;
  if(body!==undefined)headers['Content-Type']='application/json';
  let response;
  try {response=await fetch(url,{method,headers,body:form || (body===undefined?undefined:JSON.stringify(body))});}
  catch {throw errorFor({detail:'Cannot reach the server. Check your connection and try again.',code:'NETWORK_ERROR'},0);}
  let data;
  try {data=await response.json();} catch {throw errorFor({detail:'Cannot reach the KoforLink server.',code:'INVALID_RESPONSE'},response.status);}
  if(response.ok)return data;
  if(response.status===401 && retry && (data.code==='TOKEN_EXPIRED' || read('kf_refresh'))){
    if(access && access!==read('kf_access') && read('kf_access'))return request(method,path,{query,body,form},false);
    await refreshSession();return request(method,path,{query,body,form},false);
  }
  if(response.status===403 && data.code==='EMAIL_NOT_VERIFIED')window.dispatchEvent(new Event('kf:verify-email'));
  throw errorFor(data,response.status);
}
const id = value => encodeURIComponent(value);
const get = (path,query) => request('GET',path,{query});
const post = (path,body) => request('POST',path,{body});
const patch = (path,body) => request('PATCH',path,{body});
const put = (path,body) => request('PUT',path,{body});
const del = path => request('DELETE',path);
export const login=(email,password,remember)=>post('/auth/login',{email,password,remember});
export const register=body=>post('/auth/register',body);
export const requestPasswordReset=email=>post('/auth/password-reset',{email});
export const confirmPasswordReset=(email,code,newPassword)=>post('/auth/password-reset/confirm',{email,code,newPassword});
export const verifyEmail=code=>post('/auth/verify-email',{code});
export const resendCode=()=>post('/auth/resend-code');
export const changeEmail=email=>post('/auth/change-email',{email});
export async function logout(){try{return await post('/auth/logout',{refreshToken:read('kf_refresh') || null});}finally{clearTokens();}}
export const getSession=()=>get('/auth/session');
export const changePassword=(currentPassword,newPassword)=>post('/auth/change-password',{currentPassword,newPassword});
export const bootstrap=()=>get('/platform/bootstrap');
export function uploadFile(folder,file){const form=new FormData();form.append('folder',folder);form.append('file',file);return request('POST','/media',{form});}
export const getMyProfile=()=>get('/profiles/me');
export const getProfile=userId=>get('/profiles/'+id(userId));
export const updateProfile=body=>patch('/profiles/me',body);
export const uploadAvatar=(kind,fileId)=>put('/profiles/me/photo',{kind,fileId});
export const addSkill=(name,level)=>post('/profiles/me/skills',{name,level});
export const removeSkill=key=>del('/profiles/me/skills/'+id(key));
export const addExperience=body=>post('/profiles/me/experience',body);
export const deleteExperience=key=>del('/profiles/me/experience/'+id(key));
export const addEducation=body=>post('/profiles/me/education',body);
export const deleteEducation=key=>del('/profiles/me/education/'+id(key));
export const addCertification=body=>post('/profiles/me/certifications',body);
export const deleteCertification=key=>del('/profiles/me/certifications/'+id(key));
export const addProject=body=>post('/profiles/me/projects',body);
export const deleteProject=key=>del('/profiles/me/projects/'+id(key));
export const sendConnection=(userId,message)=>post('/network/connections',{userId,message});
export const respondConnection=(key,action)=>post('/network/connections/'+id(key)+'/respond',{action});
export const getConnections=userId=>get('/network/connections',{userId});
export const getConnectionRequests=()=>get('/network/requests');
export const getSuggestions=limit=>get('/network/suggestions',{limit});
export const follow=(userId,follow)=>request(follow?'PUT':'DELETE','/network/follows/'+id(userId));
export const getFollowers=(userId,mode)=>get('/network/followers',{userId,mode});
export const blockUser=(userId,block)=>request(block?'PUT':'DELETE','/network/blocks/'+id(userId));
export const getBlocked=()=>get('/network/blocks');
export const getFeed=opts=>get('/feed',opts);
export const getTrending=()=>get('/feed/trending');
export const createPost=body=>post('/feed/posts',{...body,media:(body.media || []).map(({fileId,type,caption})=>({fileId,type,caption}))});
export const getUserPosts=userId=>get('/feed/posts',{userId});
export const getSavedPosts=()=>get('/feed/posts/saved');
export const getPost=key=>get('/feed/posts/'+id(key));
export const updatePost=(key,content)=>patch('/feed/posts/'+id(key),{content});
export const deletePost=key=>del('/feed/posts/'+id(key));
export const react=(key,type)=>post('/feed/posts/'+id(key)+'/reactions',{type});
export const getComments=key=>get('/feed/posts/'+id(key)+'/comments');
export const comment=(key,content,parentId)=>post('/feed/posts/'+id(key)+'/comments',{content,parentId});
export const deleteComment=key=>del('/feed/comments/'+id(key));
export const savePost=(key,save)=>request(save?'PUT':'DELETE','/feed/posts/'+id(key)+'/save');
export const sharePost=key=>post('/feed/posts/'+id(key)+'/share');
export const getStories=()=>get('/stories');
export const createStory=({fileId,type,caption})=>post('/stories',{fileId,type,caption});
export const viewStory=key=>post('/stories/'+id(key)+'/view');
export const deleteStory=key=>del('/stories/'+id(key));
export const getCompanies=opts=>get('/companies',opts);
export const getMyCompanies=()=>get('/companies/mine');
export const nearbyCompanies=(lat,lng,radiusKm)=>get('/companies/nearby',{lat,lng,radiusKm});
export const getCompany=key=>get('/companies/'+id(key));
export const createCompany=body=>post('/companies',body);
export const updateCompany=(key,body)=>patch('/companies/'+id(key),body);
export const uploadCompanyImage=(key,kind,fileId)=>put('/companies/'+id(key)+'/image',{kind,fileId});
export const addCompanyService=(key,name,description)=>post('/companies/'+id(key)+'/services',{name,description});
export const addLocation=(key,body)=>post('/companies/'+id(key)+'/locations',body);
export const updateLocation=(key,body)=>patch('/companies/locations/'+id(key),body);
export const deleteLocation=key=>del('/companies/locations/'+id(key));
export const addLocationPhoto=(key,fileId,category,caption)=>post('/companies/locations/'+id(key)+'/photos',{fileId,category,caption});
export const deleteLocationPhoto=key=>del('/companies/location-photos/'+id(key));
export const getJobs=filters=>get('/opportunities/jobs',filters);
export const jobsNearMe=(lat,lng,radiusKm,filters)=>get('/opportunities/jobs/nearby',{...filters,lat,lng,radiusKm});
export const getJob=key=>get('/opportunities/jobs/'+id(key));
export const createJob=body=>post('/opportunities/jobs',body);
export const updateJob=(key,body)=>patch('/opportunities/jobs/'+id(key),body);
export const saveJob=(key,save)=>request(save?'PUT':'DELETE','/opportunities/jobs/'+id(key)+'/save');
export const getSavedJobs=()=>get('/opportunities/jobs/saved');
export const applyJob=(key,coverLetter,cvFileId)=>post('/opportunities/jobs/'+id(key)+'/applications',{coverLetter,cvFileId});
export const getJobApplicants=key=>get('/opportunities/jobs/'+id(key)+'/applications');
export const myApplications=()=>get('/opportunities/applications/mine');
export const withdrawApplication=key=>post('/opportunities/applications/'+id(key)+'/withdraw');
export const updateApplicationStatus=(key,status)=>patch('/opportunities/applications/'+id(key),{status});
export const createJobAlert=body=>post('/opportunities/job-alerts',body);
export const getEvents=filters=>get('/opportunities/events',filters);
export const myEvents=()=>get('/opportunities/events/mine');
export const getEvent=key=>get('/opportunities/events/'+id(key));
export const createEvent=body=>post('/opportunities/events',body);
export const updateEvent=(key,body)=>patch('/opportunities/events/'+id(key),body);
export const deleteEvent=key=>del('/opportunities/events/'+id(key));
export const eventAttendance=(key,status)=>status==='cancel'?del('/opportunities/events/'+id(key)+'/attendance'):put('/opportunities/events/'+id(key)+'/attendance',{status});
export const startConversation=(userId,message)=>post('/messaging/conversations',{userId,message});
export const createGroupConversation=(memberIds,title)=>post('/messaging/conversations/group',{memberIds,title});
export const getConversations=()=>get('/messaging/conversations');
export const getMessages=(key,sinceId)=>get('/messaging/conversations/'+id(key)+'/messages',{sinceId});
export const sendMessage=(key,body,attachment)=>post('/messaging/conversations/'+id(key)+'/messages',{body,attachment});
export const deleteMessage=key=>del('/messaging/messages/'+id(key));
export const reactMessage=(key,type)=>post('/messaging/messages/'+id(key)+'/reactions',{type});
export const searchMessages=(key,q)=>get('/messaging/conversations/'+id(key)+'/search',{q});
export const setConversationFlag=(key,flag,value)=>patch('/messaging/conversations/'+id(key)+'/settings',{[flag]:value});
export const getNotifications=limit=>get('/notifications',{limit});
export const markNotificationRead=key=>post('/notifications/'+id(key)+'/read');
export const markAllNotificationsRead=()=>post('/notifications/read-all');
export const deleteNotification=key=>del('/notifications/'+id(key));
export const search=(q,type)=>get('/search',{q,type});
export const report=(targetType,targetId,reason,details)=>post('/reports',{targetType,targetId,reason,details});
export const requestVerification=(type,companyId,note)=>post('/verification-requests',{type,companyId,note});
export const adminStats=()=>get('/admin/stats');
export const adminList=(resource,opts)=>get('/admin/resources/'+id(resource),opts);
export const adminGetVerifications=status=>get('/admin/verifications',{status});
export const adminReviewVerification=(key,decision,reason)=>post('/admin/verifications/'+id(key)+'/review',{decision,reason});
export const adminGetUser=userId=>get('/admin/users/'+id(userId));
export const adminSetUserRole=(key,role)=>put('/admin/users/'+id(key)+'/role',{role});
export const adminSetUserStatus=(key,status)=>put('/admin/users/'+id(key)+'/status',{status});
export const adminDeleteRecord=(resource,key)=>del('/admin/resources/'+id(resource)+'/'+id(key));
export const adminRestoreRecord=(resource,key)=>post('/admin/resources/'+id(resource)+'/'+id(key)+'/restore');
export const adminUpdateReport=(key,status,note)=>patch('/admin/reports/'+id(key),{status,note});
export const adminGetSettings=()=>get('/admin/settings');
export const adminSaveSettings=body=>put('/admin/settings',body);
export const companyAnalytics=key=>get('/analytics/companies/'+id(key));
export const jobAnalytics=key=>get('/analytics/jobs/'+id(key));
