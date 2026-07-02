import React from 'react'; import ReactDOM from 'react-dom/client'; import {QueryClient,QueryClientProvider} from '@tanstack/react-query'; import {CssBaseline,ThemeProvider} from '@mui/material'; import App from './App'; import {theme} from './theme';
const client=new QueryClient({defaultOptions:{queries:{retry:1,staleTime:3000}}});
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ThemeProvider theme={theme}><CssBaseline/><QueryClientProvider client={client}><App/></QueryClientProvider></ThemeProvider></React.StrictMode>);
