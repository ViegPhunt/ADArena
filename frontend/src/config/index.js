let url = '';

if (import.meta.env.DEV) {
    url = 'http://127.0.0.1:8080';
} else {
    url = window.location.origin;
}

const serverUrl = url;
const apiUrl = `${serverUrl}/api`;

const statuses = [101, 102, 103, 104, 110];

const statusesNames = {
    101: 'UP',
    102: 'CORRUPT',
    103: 'MUMBLE',
    104: 'DOWN',
    110: 'CHECK FAILED',
    '-1': 'OFFLINE',
};

const statusColors = {
    101: '#B9FBC0',
    102: '#A0C4FF',
    103: '#FFC09F',
    104: '#FFADAD',
    110: '#FDFFB6',
    '-1': '#FFC6FF'
};

const defaultStatusColor = '#F8F9FA';

export {
    serverUrl,
    apiUrl,
    statusesNames,
    statuses,
    statusColors,
    defaultStatusColor,
};