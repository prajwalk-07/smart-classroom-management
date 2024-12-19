// src/styles/dashboard.js
export const styles = {
    container: {
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
    },
    paper: {
      padding: '2rem',
      margin: '1rem',
      borderRadius: '8px',
    },
    title: {
      marginBottom: '1.5rem',
      color: '#1976d2',
    },
    card: {
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      transition: 'transform 0.2s',
      '&:hover': {
        transform: 'translateY(-4px)',
      },
    },
  };