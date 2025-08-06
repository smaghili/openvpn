# OpenVPN Manager Dashboard

A modern, responsive web dashboard for managing OpenVPN servers with comprehensive user management, traffic monitoring, and system administration features.

## Features

### 🔐 Authentication
- Secure API key authentication
- Session management
- Protected routes

### 📊 Overview Dashboard
- Real-time system statistics (CPU, RAM, Storage)
- User activity monitoring
- Service status monitoring
- Traffic visualization
- Quick backup/restore actions

### 👥 User Management
- Create/delete users
- Password management
- Quota management
- Configuration download
- Usage tracking

### ⚙️ OpenVPN Settings
- Server configuration
- Port and protocol settings
- DNS configuration
- Cipher selection
- Real-time validation

### 📈 Charts & Analytics
- Traffic analysis with interactive charts
- User activity metrics
- System health monitoring
- Data export functionality

### 🎨 Customization
- Dark/Light theme support
- Multi-language support (English/Persian)
- Responsive design
- Modern UI components

## Technology Stack

- **Frontend**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Internationalization**: i18next
- **Build Tool**: Vite
- **Notifications**: React Hot Toast

## Installation

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

3. **Build for production**:
   ```bash
   npm run build
   ```

## Configuration

### Environment Setup
The frontend automatically proxies API requests to `http://localhost:5000` during development. For production, ensure the backend API is accessible.

### API Integration
The dashboard integrates with the OpenVPN Manager API endpoints:
- `/api/users` - User management
- `/api/quota` - Traffic monitoring
- `/api/system` - System operations

## Usage

1. **Login**: Enter your API key to access the dashboard
2. **Overview**: Monitor system status and recent activity
3. **Users**: Manage VPN users, quotas, and configurations
4. **Settings**: Configure OpenVPN server parameters
5. **Charts**: Analyze traffic patterns and usage
6. **General**: Customize appearance and API settings

## API Key Authentication

The dashboard uses API key authentication. You can:
- Set the API key via environment variable `OPENVPN_API_KEY`
- Generate new keys through the General Settings page
- Copy/view existing keys securely

## Responsive Design

The dashboard is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile devices

## Internationalization

Supports multiple languages:
- English (default)
- Persian/Farsi

Add new languages by creating translation files in `src/i18n/locales/`.

## Theme Support

- **Light Theme**: Clean, bright interface
- **Dark Theme**: Easy on the eyes for extended use
- **Auto-detection**: Respects system preferences

## Development

### Project Structure
```
src/
├── components/     # Reusable UI components
├── pages/         # Page components
├── contexts/      # React contexts (theme, auth)
├── lib/           # Utilities and API client
├── types/         # TypeScript type definitions
└── i18n/          # Internationalization
```

### Adding New Features
1. Create components in appropriate directories
2. Add TypeScript types in `src/types/`
3. Update API client if needed
4. Add translations for new text
5. Test responsive behavior

## Production Deployment

1. Build the project: `npm run build`
2. Serve the `dist` folder using a web server
3. Configure reverse proxy to backend API
4. Set appropriate environment variables

## Security Considerations

- API keys are stored securely in localStorage
- All API requests include authentication headers
- Input validation on all forms
- XSS protection through React's built-in sanitization

## Browser Support

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Include translations for new text
4. Test on multiple screen sizes
5. Ensure accessibility standards