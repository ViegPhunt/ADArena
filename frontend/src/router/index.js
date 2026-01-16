import { createRouter, createWebHistory } from 'vue-router';
import axios from 'axios';
import { serverUrl } from '@/config';

const Scoreboard = () => import('@/features/scoreboard/views/Scoreboard.vue');
const LiveScoreboard = () => import('@/features/scoreboard/views/Live.vue');
const TeamScoreboard = () => import('@/features/scoreboard/views/TeamScoreboard.vue');

const AdminLogin = () => import('@/features/admin/views/Login.vue');
const AdminScoreboard = () => import('@/features/admin/views/AdminScoreboard.vue');
const TaskAdmin = () => import('@/features/admin/views/Task.vue');
const TeamAdmin = () => import('@/features/admin/views/Team.vue');
const AdminTeamTaskLog = () => import('@/features/admin/views/TeamTaskLog.vue');

const routes = [
    {
        path: '/',
        name: 'index',
        component: Scoreboard,
    },
    {
        path: '/live/',
        name: 'live',
        component: LiveScoreboard,
        meta: {
            layout: 'empty',
        },
    },
    {
        path: '/team/:id/',
        name: 'team',
        component: TeamScoreboard,
    },
    {
        path: '/admin/login/',
        name: 'adminLogin',
        component: AdminLogin,
    },
    {
        path: '/admin/',
        name: 'admin',
        component: AdminScoreboard,
        meta: {
            auth: true,
        },
    },
    {
        path: '/admin/task/:id/',
        name: 'taskAdmin',
        component: TaskAdmin,
        meta: {
            auth: true,
        },
    },
    {
        path: '/admin/team/:id/',
        name: 'teamAdmin',
        component: TeamAdmin,
        meta: {
            auth: true,
        },
    },
    {
        path: '/admin/create_task/',
        name: 'createTask',
        component: TaskAdmin,
        meta: {
            auth: true,
        },
    },
    {
        path: '/admin/create_team/',
        name: 'createTeam',
        component: TeamAdmin,
        meta: {
            auth: true,
        },
    },
    {
        path: '/admin/teamtask_log/team/:teamId/task/:taskId/',
        name: 'adminTeamTaskLog',
        component: AdminTeamTaskLog,
        meta: {
            auth: true,
        },
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, from, next) => {
    if (to.meta.auth) {
        try {
            await axios.get(`${serverUrl}/api/admin/status/`);
            next();
        } catch (e) {
            next({ name: 'adminLogin' });
        }
    } else {
        next();
    }
});

export default router;