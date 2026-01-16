import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import pinia from './stores';
import axios from 'axios';
import { apiUrl } from '@/config';
import FloatingVue from 'floating-vue';
import 'floating-vue/dist/style.css';
import '@fortawesome/fontawesome-free/css/all.css';

// Axios configuration
axios.defaults.baseURL = apiUrl;
axios.defaults.withCredentials = true;

const app = createApp(App);

// Make axios available globally
app.config.globalProperties.$http = axios;

// Use plugins
app.use(pinia);
app.use(router);
app.use(FloatingVue, {
    themes: {
        tooltip: {
            delay: {
                show: 200,
                hide: 100,
            },
        },
    },
});

// Mount app
app.mount('#app');
