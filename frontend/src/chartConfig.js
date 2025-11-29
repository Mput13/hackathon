import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  BubbleController,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

// Global registration of all Chart.js components used in the app
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  BubbleController,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Set Defaults
ChartJS.defaults.color = '#9ca3af'
ChartJS.defaults.borderColor = '#2D2D2D'
ChartJS.defaults.font.family = 'Bahnschrift'