import {
    statusColors,
    defaultStatusColor,
} from '@/config';

function getTeamTaskBackground(status) {
    return statusColors[status] ? statusColors[status] : defaultStatusColor;
}

export { getTeamTaskBackground };
