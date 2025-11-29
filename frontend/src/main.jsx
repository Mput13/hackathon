import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './fonts.css'
import './index.css'
import './chartConfig' // Register Chart.js components globally

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)