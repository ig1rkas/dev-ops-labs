const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

export const SESSION_STORAGE_KEY = 'idioma.session';

async function request(path, options = {}) {
  const { formData = false, ...fetchOptions } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(formData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      ...options.headers,
    },
    ...fetchOptions,
  });

  const text = await response.text();
  let data = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text || 'Не удалось выполнить запрос' };
  }

  if (!response.ok) {
    throw new Error(data?.detail || 'Не удалось выполнить запрос');
  }

  return data;
}

export function fetchSubjects() {
  return request('/subjects');
}

export function createAdminSubject(token, payload) {
  return request('/admin/subjects', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export function deleteAdminSubject(token, subjectId) {
  return request(`/admin/subjects/${subjectId}`, {
    method: 'DELETE',
    token,
  });
}

export function fetchTeachers() {
  return request('/teachers');
}

export function login(payload) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function register(payload) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getMe(token) {
  return request('/auth/me', { token });
}

export function changePassword(token, currentPassword, newPassword) {
  return request('/auth/password', {
    method: 'PATCH',
    token,
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export function fetchStudentDashboard(token) {
  return request('/dashboard/student', { token });
}

export function fetchTeacherDashboard(token, refreshCalendar = false) {
  const suffix = refreshCalendar ? '?refresh_calendar=true' : '';
  return request(`/dashboard/teacher${suffix}`, { token });
}

export function fetchAdminDashboard(token) {
  return request('/dashboard/admin', { token });
}

export function fetchChats(token) {
  return request('/messages/chats', { token });
}

export function fetchTelegramStatus(token) {
  return request('/messages/status', { token });
}

export function fetchChat(token, chatId) {
  return request(`/messages/chats/${chatId}`, { token });
}

export function sendChatMessage(token, chatId, body) {
  return request(`/messages/chats/${chatId}/messages`, {
    method: 'POST',
    token,
    body: JSON.stringify({ body }),
  });
}

export function sendChatPhoto(token, chatId, photo, caption = '') {
  const form = new FormData();
  form.append('photo', photo);
  form.append('caption', caption);
  return request(`/messages/chats/${chatId}/photos`, {
    method: 'POST',
    token,
    body: form,
    formData: true,
  });
}

export function sendChatDocument(token, chatId, document, caption = '') {
  const form = new FormData();
  form.append('document', document);
  form.append('caption', caption);
  return request(`/messages/chats/${chatId}/documents`, {
    method: 'POST',
    token,
    body: form,
    formData: true,
  });
}

export async function fetchChatDocument(token, chatId, messageId) {
  const response = await fetch(`${API_BASE}/messages/chats/${chatId}/messages/${messageId}/document`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    let detail = 'Не удалось скачать файл';
    try {
      detail = (await response.json()).detail || detail;
    } catch {
      // A transient network or proxy error may return an empty body.
    }
    throw new Error(detail);
  }
  return response.blob();
}

export async function fetchChatPhoto(token, chatId, messageId) {
  const response = await fetch(`${API_BASE}/messages/chats/${chatId}/messages/${messageId}/photo`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    let detail = 'Не удалось загрузить фото';
    try {
      detail = (await response.json()).detail || detail;
    } catch {
      // A transient network or proxy error may return an empty body.
    }
    throw new Error(detail);
  }
  return URL.createObjectURL(await response.blob());
}

export function deleteChatMessage(token, chatId, messageId) {
  return request(`/messages/chats/${chatId}/messages/${messageId}`, {
    method: 'DELETE',
    token,
  });
}

export function createCourseRequest(token, payload) {
  return request('/course-requests', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export function createTeacherApplication(payload) {
  return request('/teacher-applications', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchAdminUsers(token, role = 'all', q = '') {
  const params = new URLSearchParams();
  if (role && role !== 'all') params.set('role', role);
  if (q) params.set('q', q);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return request(`/admin/users${suffix}`, { token });
}

export function fetchAdminUser(token, userId) {
  return request(`/admin/users/${userId}`, { token });
}

export function createAdminStudent(token, payload) {
  return request('/admin/students', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export function fetchTeacherStudents(token, teacherUserId) {
  return request(`/admin/teachers/${teacherUserId}/students`, { token });
}

export function assignStudentToTeacher(token, teacherUserId, studentId) {
  return request(`/admin/teachers/${teacherUserId}/students`, {
    method: 'POST',
    token,
    body: JSON.stringify({ student_id: Number(studentId) }),
  });
}

export function removeStudentFromTeacher(token, teacherUserId, assignmentId) {
  return request(`/admin/teachers/${teacherUserId}/students/${assignmentId}`, {
    method: 'DELETE',
    token,
  });
}

export function createAdminTeacher(token, payload) {
  return request('/admin/teachers', {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export function updateAdminTeacher(token, teacherUserId, payload) {
  return request(`/admin/teachers/${teacherUserId}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}

export function reorderAdminTeacher(token, teacherUserId, action) {
  return request(`/admin/teachers/${teacherUserId}/position`, {
    method: 'PATCH',
    token,
    body: JSON.stringify({ action }),
  });
}

export function deleteAdminUser(token, userId) {
  return request(`/admin/users/${userId}`, { method: 'DELETE', token });
}

export function updateTeacherStudentDisplayName(token, assignmentId, displayName) {
  return request(`/teacher/students/${assignmentId}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify({ display_name: displayName?.trim() || null }),
  });
}

export function fetchCourseRequests(token, status = 'new') {
  const params = new URLSearchParams();
  if (status && status !== 'all') params.set('status_filter', status);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return request(`/admin/course-requests${suffix}`, { token });
}

export function fetchTeacherApplications(token, status = 'new') {
  const params = new URLSearchParams();
  if (status && status !== 'all') params.set('status_filter', status);
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return request(`/admin/teacher-applications${suffix}`, { token });
}

export function scheduleCourseRequest(token, requestId, payload) {
  return request(`/admin/course-requests/${requestId}/schedule`, {
    method: 'POST',
    token,
    body: JSON.stringify(payload),
  });
}

export function deleteCourseRequest(token, requestId) {
  return request(`/admin/course-requests/${requestId}`, {
    method: 'DELETE',
    token,
  });
}

export function deleteTeacherApplication(token, applicationId) {
  return request(`/admin/teacher-applications/${applicationId}`, {
    method: 'DELETE',
    token,
  });
}

export function updateStudentSettings(token, payload) {
  return request('/dashboard/student/settings', {
    method: 'PATCH',
    token,
    body: JSON.stringify(payload),
  });
}
