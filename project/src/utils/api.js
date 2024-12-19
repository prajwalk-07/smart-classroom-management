import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

// Create axios instance with default config
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Add auth token to requests if available
api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    response => response,
    error => {
        if (error.response) {
            switch (error.response.status) {
                case 401:
                    localStorage.clear();
                    window.location.href = '/login';
                    break;
                case 403:
                    console.error('Access denied');
                    break;
                case 404:
                    console.error('Resource not found');
                    break;
                default:
                    console.error('API Error:', error.response.data);
            }
        }
        return Promise.reject(error);
    }
);

// API endpoints
const endpoints = {
    // Auth endpoints
    auth: {
        login: (data) => api.post('/auth/login', data),
        logout: () => api.post('/auth/logout'),
        register: (data) => api.post('/auth/register', data)
    },

    // Student endpoints
    student: {
        getAttendance: () => api.get('/student/attendance'),
        getIAMarks: () => api.get('/student/ia-marks'),
        getAssignments: () => api.get('/student/assignments'),
        monitorActivity: (imageData) => {
            const formData = new FormData();
            formData.append('image', imageData);
            return api.post('/student/monitor', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
        },
        submitAssignment: (assignmentId, file) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('assignment_id', assignmentId);
            return api.post('/student/submit-assignment', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
        }
    },

    // Teacher endpoints
    teacher: {
        getStudents: () => api.get('/teacher/students'),
        getAttendance: () => api.get('/teacher/attendance'),
        submitAttendance: (data) => api.post('/teacher/attendance', data),
        getAssignments: () => api.get('/teacher/assignments'),
        submitMarks: (data) => api.post('/teacher/marks', data),
        getIAMarks: () => api.get('/teacher/ia-marks')
    },

    // Parent endpoints
    parent: {
        getStudentDetails: () => api.get('/parent/student-details'),
        getAttendance: () => api.get('/parent/student-attendance'),
        getIAMarks: () => api.get('/parent/student-ia-marks')
    }
};

export default endpoints;