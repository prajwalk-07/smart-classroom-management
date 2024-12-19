import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  List,
  Chip
} from '@mui/material';
import { CloudUpload as UploadIcon } from '@mui/icons-material';

const AssignmentUpload = () => {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);

  useEffect(() => {
    fetchRecoveryAssignments();
  }, []);

  const fetchRecoveryAssignments = async () => {
    try {
      setLoading(true);
      const user = JSON.parse(localStorage.getItem('user'));
      if (!user || !user.role_id) {
        throw new Error('User data not found');
      }

      // First fetch attendance to check for consecutive absences
      const attendanceResponse = await axios.get(`http://localhost:5000/student/attendance`, {
        params: { student_id: user.role_id }
      });

      if (attendanceResponse.data.status === 'success') {
        // Check for consecutive absences
        const absences = attendanceResponse.data.data.filter(record => record.status === 0);
        if (absences.length >= 3) {
          // If there are consecutive absences, fetch recovery assignments
          const response = await axios.get(`http://localhost:5000/student/recovery-assignments`, {
            params: { student_id: user.role_id }
          });

          if (response.data.status === 'success') {
            setAssignments(response.data.data);
            setError('');
          }
        }
      }
    } catch (error) {
      console.error('Error fetching assignments:', error);
      setError(error.message || 'Failed to fetch assignments');
    } finally {
      setLoading(false);
    }
  };
  const handleFileUpload = async (event, assignmentId) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('File size should be less than 5MB');
      return;
    }

    // Validate file type
    const validFileTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!validFileTypes.includes(file.type)) {
      setError('Invalid file type. Please upload a .doc, .docx, or .pdf file.');
      return;
    }

    setUploadLoading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('student_id', JSON.parse(localStorage.getItem('user')).role_id);
    formData.append('assignment_id', assignmentId);

    try {
      // First check if already submitted
      const checkResponse = await axios.get(
        `http://localhost:5000/student/check-submission/${assignmentId}`,
        {
            params: { 
                student_id: JSON.parse(localStorage.getItem('user')).role_id 
            }
        }
    );
      if (checkResponse.data.submitted) {
        setError('You have already submitted this assignment.');
        setUploadLoading(false);
        return;
      }

      const response = await axios.post(
        'http://localhost:5000/student/submit-assignment',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      if (response.data.status === 'success') {
        setSuccess(`Assignment uploaded successfully`);
        // Update the local assignments state
        setAssignments(prevAssignments => 
          prevAssignments.map(assignment => 
            assignment.id === assignmentId 
              ? { 
                  ...assignment, 
                  submission_status: 'completed',
                }
              : assignment
          )
        );
      }
    } catch (error) {
      console.error('Error during assignment upload:', error);
      setError(error.response?.data?.message || 'Failed to upload assignment');
    } finally {
      setUploadLoading(false);
    }
  };
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" m={3}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Recovery Assignments
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      {assignments.length > 0 ? (
        <List>
        {assignments.map((assignment, index) => (
    <Paper key={`${assignment.id}-${index}`} sx={{ mb: 2, p: 2 }}> {/* Combine id with index */}
        <Typography variant="h6">{assignment.title}</Typography>
        <Typography color="textSecondary" gutterBottom>
            Due Date: {new Date(assignment.due_date).toLocaleDateString()}
        </Typography>
        <Typography variant="body1" sx={{ mb: 2 }}>
            Subject: {assignment.subject_name}
        </Typography>
        <Typography variant="body1" sx={{ mb: 2 }}>
            Questions:
        </Typography>
        {assignment.questions && assignment.questions.map((question, qIndex) => (
            <Typography key={qIndex} sx={{ mb: 1 }}>
                {question}
            </Typography>
        ))}
        {assignment.submission_status ? (
            <Chip 
                label={`Submitted Successfully`}
                color="success"
                sx={{ mt: 2 }}
            />
        ) : (
            <Button
                variant="contained"
                color="primary"
                component="label"
                disabled={uploadLoading}
                startIcon={<UploadIcon />}
                sx={{ mt: 2 }}
            >
                {uploadLoading ? <CircularProgress size={24} /> : 'Upload Assignment'}
                <input
                    type="file"
                    hidden
                    onChange={(e) => handleFileUpload(e, assignment.id)}
                />
            </Button>
        )}
    </Paper>
))}
        </List>
      ) : (
        <Alert severity="info">No recovery assignments pending</Alert>
      )}
    </Box>
  );
};

export default AssignmentUpload;