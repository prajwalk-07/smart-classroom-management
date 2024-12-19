import React, { useState, useEffect } from 'react';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  CircularProgress,
  Box,
  Alert,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  School as SchoolIcon,
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';
import axios from 'axios';

const IAMarks = () => {
  const [marks, setMarks] = useState([]);
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [performanceSummary, setPerformanceSummary] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      if (!user || !user.role_id) {
        throw new Error('User data not found');
      }

      setLoading(true);

      // Fetch marks and recommendations in parallel
      const [marksResponse, recommendationsResponse] = await Promise.all([
        axios.get('http://localhost:5000/student/marks', {
          params: { student_id: user.role_id }
        }),
        axios.get('http://localhost:5000/student/course-recommendations', {
          params: { student_id: user.role_id }
        })
      ]);

      if (marksResponse.data.status === 'success') {
        setMarks(marksResponse.data.data);
        calculatePerformanceSummary(marksResponse.data.data);
      }

      if (recommendationsResponse.data.status === 'success') {
        setRecommendations(recommendationsResponse.data.data.recommendations);
      }

      setError('');
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const calculatePerformanceSummary = (marksData) => {
    const summary = {};
    
    marksData.forEach(mark => {
      if (!summary[mark.subject_name]) {
        summary[mark.subject_name] = {
          totalMarks: 0,
          obtainedMarks: 0,
          assessments: 0,
          percentage: 0
        };
      }
      
      summary[mark.subject_name].totalMarks += mark.total_marks;
      summary[mark.subject_name].obtainedMarks += mark.marks_obtained;
      summary[mark.subject_name].assessments += 1;
    });

    // Calculate percentages
    Object.keys(summary).forEach(subject => {
      summary[subject].percentage = 
        (summary[subject].obtainedMarks / summary[subject].totalMarks) * 100;
    });

    setPerformanceSummary(summary);
  };

  const getPerformanceColor = (percentage) => {
    if (percentage >= 75) return 'success';
    if (percentage >= 60) return 'warning';
    return 'error';
  };

  const getPerformanceLabel = (percentage) => {
    if (percentage >= 75) return 'Excellent';
    if (percentage >= 60) return 'Good';
    return 'Needs Improvement';
  };

  const renderPerformanceSummary = () => {
    return (
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {Object.entries(performanceSummary).map(([subject, data]) => (
          <Grid item xs={12} sm={6} md={4} key={subject}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {subject}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Chip
                    label={`${data.percentage.toFixed(1)}%`}
                    color={getPerformanceColor(data.percentage)}
                    icon={data.percentage >= 60 ? <TrendingUpIcon /> : <TrendingDownIcon />}
                  />
                  <Typography variant="body2" color="text.secondary">
                    {getPerformanceLabel(data.percentage)}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Total Assessments: {data.assessments}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  };

  const renderMarksTable = () => {
    return (
      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Subject</TableCell>
              <TableCell>Assessment Type</TableCell>
              <TableCell align="right">Marks Obtained</TableCell>
              <TableCell align="right">Total Marks</TableCell>
              <TableCell align="right">Percentage</TableCell>
              <TableCell>Date</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {marks.map((mark) => {
              const percentage = (mark.marks_obtained / mark.total_marks) * 100;
              return (
                <TableRow key={mark.id}>
                  <TableCell>{mark.subject_name}</TableCell>
                  <TableCell>{mark.assessment_type}</TableCell>
                  <TableCell align="right">{mark.marks_obtained}</TableCell>
                  <TableCell align="right">{mark.total_marks}</TableCell>
                  <TableCell align="right">
                    <Chip
                      label={`${percentage.toFixed(1)}%`}
                      size="small"
                      color={getPerformanceColor(percentage)}
                    />
                  </TableCell>
                  <TableCell>{new Date(mark.date).toLocaleDateString()}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  const renderRecommendations = () => {
    if (!recommendations) return null;
  
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SchoolIcon color="primary" />
            Recommended Courses
          </Typography>
          <Divider sx={{ my: 2 }} />
          {Object.entries(recommendations).map(([subject, data]) => {
            // Ensure performance is a number
            const performance = typeof data.performance === 'number' ? 
              data.performance : parseFloat(data.performance) || 0;
  
            return (
              <Accordion key={subject} sx={{ mb: 1 }}>
                <AccordionSummary 
                  expandIcon={<ExpandMoreIcon />}
                  sx={{
                    backgroundColor: 'action.hover'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    <Typography variant="subtitle1" color="primary">
                      {subject}
                    </Typography>
                    <Chip 
                      label={`${performance.toFixed(1)}%`}
                      color={getPerformanceColor(performance)}
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary">
                      Level: {data.level}
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ pl: 2 }}>
                    {data.courses.map((course, index) => (
                      <Box 
                        key={index} 
                        sx={{ 
                          mb: 2, 
                          p: 2, 
                          bgcolor: 'background.paper',
                          borderRadius: 1,
                          '&:last-child': { mb: 0 } 
                        }}
                      >
                        <Typography variant="subtitle2" color="primary" gutterBottom>
                          {course.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          Platform: {course.platform}
                        </Typography>
                        <Typography variant="body2" paragraph>
                          {course.description}
                        </Typography>
                        <Chip 
                          label={course.difficulty}
                          size="small"
                          color={
                            course.difficulty === 'Advanced' ? 'success' :
                            course.difficulty === 'Intermediate' ? 'warning' : 
                            'error'
                          }
                        />
                      </Box>
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            );
          })}
        </CardContent>
      </Card>
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', m: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ m: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Academic Performance
      </Typography>

      {/* Performance Summary Cards */}
      {renderPerformanceSummary()}

      {/* Detailed Marks Table */}
      <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
        Assessment Details
      </Typography>
      {marks.length === 0 ? (
        <Alert severity="info">No marks data available</Alert>
      ) : (
        renderMarksTable()
      )}

      {/* Course Recommendations */}
      {recommendations && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="h6" gutterBottom>
            Personalized Learning Recommendations
          </Typography>
          {renderRecommendations()}
        </Box>
      )}
    </Box>
  );
};

export default IAMarks;