import React, { useState } from 'react';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  Menu as MenuIcon,
  School as SchoolIcon,
  Monitor as MonitorIcon,
  Assessment as AssessmentIcon,
  Assignment as AssignmentIcon,
  ExitToApp as LogoutIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import Attendance from './Attendance';
import ClassMonitoring from './ClassMonitoring';
import IAMarks from './IAMarks';
import AssignmentUpload from './AssignmentUpload';

const StudentDashboard = () => {
  const [currentComponent, setCurrentComponent] = useState('attendance');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/');
  };

  const renderComponent = () => {
    switch(currentComponent) {
      case 'attendance':
        return <Attendance />;
      case 'classMonitoring':
        return <ClassMonitoring />;
      case 'iaMarks':
        return <IAMarks />;
      case 'assignments':
        return <AssignmentUpload />;
      default:
        return <Attendance />;
    }
  };

  const menuItems = [
    { text: 'Attendance', icon: <SchoolIcon />, component: 'attendance' },
    { text: 'Class Monitoring', icon: <MonitorIcon />, component: 'classMonitoring' },
    { text: 'IA Marks', icon: <AssessmentIcon />, component: 'iaMarks' },
    { text: 'Assignments', icon: <AssignmentIcon />, component: 'assignments' },
    { text: 'Logout', icon: <LogoutIcon />, action: handleLogout }
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed">
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setDrawerOpen(!drawerOpen)}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            Student Dashboard
          </Typography>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="temporary"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        <Toolbar />
        <Divider />
        <List>
          {menuItems.map((item) => (
            <ListItem
              button
              key={item.text}
              onClick={() => {
                if (item.action) {
                  item.action();
                } else {
                  setCurrentComponent(item.component);
                  setDrawerOpen(false);
                }
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        {renderComponent()}
      </Box>
    </Box>
  );
};

export default StudentDashboard;