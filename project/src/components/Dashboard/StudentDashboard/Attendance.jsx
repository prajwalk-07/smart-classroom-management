import React, { useState, useEffect } from 'react';

import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  CircularProgress,
  Button,
  Alert,
  Card,
  CardContent
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Class as ClassIcon,
  Person as PersonIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import axios from 'axios';

const Attendance = () => {
  const [attendance, setAttendance] = useState([]);
  const [currentClass, setCurrentClass] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    fetchAttendance();
    fetchCurrentClass();
    // Refresh current class every minute
    const interval = setInterval(fetchCurrentClass, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchCurrentClass = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      if (!user || !user.role_id) {
        throw new Error('User data not found');
      }

      const response = await axios.get(`http://localhost:5000/current-class`, {
        params: { student_id: user.role_id }
      });

      if (response.data.status === 'success') {
        // Ensure is_present is properly set as a boolean
        const classData = {
          ...response.data.data,
          is_present: Boolean(response.data.data.is_present)
        };
        setCurrentClass(classData);
        setError('');
      } else {
        setCurrentClass(null);
      }
    } catch (err) {
      console.error('Error fetching current class:', err);
      setCurrentClass(null);
    }
  };

  const fetchAttendance = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      if (!user || !user.role_id) {
        throw new Error('User data not found');
      }

      const response = await axios.get(`http://localhost:5000/student/attendance`, {
        params: { student_id: user.role_id }
      });

      if (response.data.status === 'success') {
        setAttendance(response.data.data);
      } else {
        setError('Failed to fetch attendance data');
      }
    } catch (err) {
      console.error('Error fetching attendance:', err);
      setError(err.message || 'Failed to fetch attendance data');
    } finally {
      setLoading(false);
    }
  };

  const markPresent = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      if (!user || !user.role_id || !currentClass) {
        throw new Error('Required information not found');
      }

      setLoading(true);
      const response = await axios.post('http://localhost:5000/attendance/mark-present', {
        student_id: user.role_id,
        subject_id: currentClass.subject_id
      });

      if (response.data.status === 'success') {
        setSuccessMessage('Successfully marked as present!');
        // Update current class locally
        setCurrentClass(prev => ({
          ...prev,
          is_present: true
        }));
        // Refresh attendance history
        await fetchAttendance();
        // Clear success message after 3 seconds
        setTimeout(() => setSuccessMessage(''), 3000);
      }
    } catch (err) {
      console.error('Error marking attendance:', err);
      setError(err.response?.data?.message || 'Failed to mark attendance');
      setTimeout(() => setError(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {currentClass ? (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Current Class
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <ClassIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">
                {currentClass.subject_name} ({currentClass.subject_code})
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <PersonIcon sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography color="text.secondary">
                  Teacher: {currentClass.teacher_name}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <ScheduleIcon sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography color="text.secondary">
                  Time: {currentClass.formatted_start_time} - {currentClass.formatted_end_time}
                </Typography>
              </Box>
            </Box>

            <Button
              variant="contained"
              color="primary"
              startIcon={<CheckCircleIcon />}
              onClick={markPresent}
              disabled={loading || currentClass.is_present === true}
              fullWidth
            >
              {currentClass.is_present ? 'Already Marked Present' : 'Mark as Present'}
            </Button>
            {successMessage && (
              <Alert severity="success" sx={{ mt: 2 }}>
                {successMessage}
              </Alert>
            )}
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info" sx={{ mb: 3 }}>
          No ongoing class at the moment
        </Alert>
      )}

      {/* Attendance History Table */}
      <Typography variant="h5" gutterBottom>
        Attendance Record
      </Typography>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', m: 3 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Typography color="error" sx={{ m: 2 }}>
          {error}
        </Typography>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Subject</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {attendance.map((record, index) => (
                <TableRow 
                  key={index}
                  sx={{
                    backgroundColor: record.status === 1 ? 
                      'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)'
                  }}
                >
                  <TableCell>{record.date}</TableCell>
                  <TableCell>{record.subject}</TableCell>
                  <TableCell>
                    <Box
                      sx={{
                        display: 'inline-block',
                        px: 2,
                        py: 0.5,
                        borderRadius: 1,
                        backgroundColor: record.status === 1 ? 
                          'rgba(76, 175, 80, 0.2)' : 'rgba(244, 67, 54, 0.2)',
                        color: record.status === 1 ? 'success.dark' : 'error.dark'
                      }}
                    >
                      {record.status === 1 ? 'Present' : 'Absent'}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default Attendance;