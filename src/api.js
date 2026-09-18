const API = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';
let token = localStorage.getItem('faceclass_token');

export const setToken = value => { token = value; value ? localStorage.setItem('faceclass_token', value) : localStorage.removeItem('faceclass_token'); };

export async function request(path, options = {}) {
  const headers = { ...(options.body instanceof FormData ? {} : {'Content-Type':'application/json'}), ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API}${path}`, {...options, headers});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(data.message || 'Request failed'), { code: data.code, status: response.status });
  return data;
}

export const api = {
  login: body => request('/auth/login', {method:'POST', body:JSON.stringify(body)}),
  register: body => request('/auth/register', {method:'POST', body:JSON.stringify(body)}),
  profile: () => request('/user/profile'),
  updateProfile: body => request('/user/profile', {method:'PUT', body:JSON.stringify(body)}),
  predictions: query => request(`/predictions${query ? `?${query}` : ''}`),
  prediction: id => request(`/predictions/${id}`),
  predict: file => { const body = new FormData(); body.append('image', file); return request('/predictions', {method:'POST', body}); },
  removePrediction: id => request(`/predictions/${id}`, {method:'DELETE'}),
  analytics: () => request('/analytics/overview'),
  model: () => request('/model'),
  admin: () => request('/admin/overview')
};

