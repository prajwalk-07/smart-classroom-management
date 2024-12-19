import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Box, Typography, CircularProgress } from '@mui/material';

const ClassMonitoring = () => {
  const videoRef = useRef(null);
  const isAnalyzing = useRef(false);
  const [status, setStatus] = useState('active');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [inactivityCount, setInactivityCount] = useState(0);
  const [notificationMessage, setNotificationMessage] = useState('');

  const startVideoStream = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error('Camera access error:', err);
      setError('Failed to access camera. Please check camera permissions.');
    }
  };

  const captureAndAnalyze = async () => {
    if (isAnalyzing.current || isProcessing) return;
    
    try {
        isAnalyzing.current = true;
        setIsProcessing(true);
        setError('');
        
        // Create canvas and capture image
        const video = videoRef.current;
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas to blob
        const blob = await new Promise(resolve => 
            canvas.toBlob(resolve, 'image/jpeg', 0.95)
        );
        
        // Create FormData object
        const formData = new FormData();
        formData.append('image', blob, 'capture.jpg');
        
        // Get user data from localStorage
        const user = JSON.parse(localStorage.getItem('user'));
        formData.append('student_id', user?.role_id);
        formData.append('inactivity_count', inactivityCount.toString());

        const response = await axios.post(
            'http://localhost:5000/analyze-stream',
            formData,
            {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                timeout: 10000
            }
        );

        if (response.data.status === 'success') {
            setStatus(response.data.expression);
            
            if (response.data.notification_sent) {
                setNotificationMessage(response.data.notification_message);
                // Reset count after successful notification
                setInactivityCount(0);
                setTimeout(() => {
                    setNotificationMessage('');
                }, 3000);
            } else if (response.data.expression === 'inactive') {
                if (inactivityCount < 5) {
                    setInactivityCount(prevCount => prevCount + 1);
                }
            } else {
                // Reset when student becomes active
                setInactivityCount(0);
                setNotificationMessage('');
            }
        } else {
            setError(response.data.message || 'Analysis failed');
        }
        
    } catch (error) {
        console.error('Analysis error:', error);
        setError(error.response?.data?.message || 'Failed to analyze activity');
    } finally {
        isAnalyzing.current = false;
        setIsProcessing(false);
    }
};

// Update the useEffect to handle the interval
useEffect(() => {
    startVideoStream();
    
    // Only start interval if count is less than 5
    const intervalId = setInterval(() => {
        if (inactivityCount <= 5) {
            captureAndAnalyze();
        }
    }, 5000);

    return () => {
        clearInterval(intervalId);
        if (videoRef.current?.srcObject) {
            const tracks = videoRef.current.srcObject.getTracks();
            tracks.forEach(track => track.stop());
        }
    };
}, [inactivityCount]); // Add inactivityCount as dependency

  return (
    <Box sx={{ p: 3 }}>
    <Typography variant="h5" gutterBottom>
        Class Monitoring
    </Typography>

    {error && (
        <Typography color="error" sx={{ mb: 2 }}>
            {error}
        </Typography>
    )}

    <Box sx={{ 
        position: 'relative', 
        width: '100%', 
        maxWidth: 640, 
        mx: 'auto',
        bgcolor: 'background.paper',
        borderRadius: 2,
        boxShadow: 3,
        overflow: 'hidden'
    }}>
        <video 
            ref={videoRef} 
            autoPlay 
            playsInline
            style={{ width: '100%', borderRadius: '8px 8px 0 0' }} 
        />
        
        <Box sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ 
                color: status === 'active' ? 'success.main' : 'error.main',
                display: 'flex',
                alignItems: 'center',
                gap: 1
            }}>
                Status: {status}
                {isProcessing && <CircularProgress size={20} />}
            </Typography>
            
            {inactivityCount > 0 && (
                <Typography 
                    color="warning.main"
                    sx={{ 
                        mt: 1,
                        p: 1,
                        bgcolor: 'warning.light',
                        borderRadius: 1
                    }}
                >
                    ⚠️ Warning: Inactivity detected ({inactivityCount}/5)
                </Typography>
            )}
            
            {notificationMessage && (
                <Typography 
                    sx={{ 
                        mt: 2,
                        p: 2,
                        bgcolor: 'info.light',
                        borderRadius: 1,
                        color: 'info.contrastText',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1
                    }}
                >
                    📱 {notificationMessage}
                </Typography>
            )}
        </Box>
    </Box>
</Box>
  );
};

export default ClassMonitoring;