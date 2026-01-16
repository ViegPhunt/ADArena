<template>
    <div class="flag">
        <error-box :error="error">
            <div
                v-for="({ attacker, victim, task, delta }, index) in events"
                :key="index"
            >
                <span class="mark">{{ attacker }}</span> stole a flag from
                <span class="mark">{{ victim }}</span
                >'s service <span class="mark">{{ task }}</span> and got
                <span class="mark">{{ delta }}</span> points
            </div>
        </error-box>
    </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, getCurrentInstance } from 'vue';
import { serverUrl } from '@/config';
import ErrorBox from '@/components/ui/ErrorBox.vue';

export default {
    components: {
        ErrorBox,
    },

    setup() {
        const { proxy } = getCurrentInstance();
        
        const error = ref(null);
        const ws = ref(null);
        const teams = ref(null);
        const tasks = ref(null);
        const events = ref([]);
        const reconnectAttempts = ref(0);
        const maxReconnectAttempts = 10;

        const connectWebSocket = () => {
            const wsUrl = serverUrl.replace(/^http/, 'ws');
            ws.value = new WebSocket(`${wsUrl}/api/events/ws/live_events`);

            ws.value.onopen = () => {
                console.log('WebSocket connected to live events');
                error.value = null;
                reconnectAttempts.value = 0;
            };

            ws.value.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    
                    if (message.event === 'flag_stolen') {
                        error.value = null;
                        const {
                            attacker_id: attackerId,
                            victim_id: victimId,
                            task_id: taskId,
                            attacker_delta: delta,
                        } = message.data;

                        events.value.unshift({
                            attacker: teams.value.filter(({ id }) => id === attackerId)[0].name,
                            victim: teams.value.filter(({ id }) => id === victimId)[0].name,
                            task: tasks.value.filter(({ id }) => id == taskId)[0].name,
                            delta,
                        });
                    }
                } catch (err) {
                    console.error('Error parsing WebSocket message:', err);
                }
            };

            ws.value.onerror = (err) => {
                console.error('WebSocket error:', err);
                error.value = "Can't connect to server";
            };

            ws.value.onclose = () => {
                console.log('WebSocket disconnected');
                
                if (reconnectAttempts.value < maxReconnectAttempts) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000);
                    reconnectAttempts.value++;
                    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value})`);
                    setTimeout(() => connectWebSocket(), delay);
                } else {
                    console.error('Max reconnection attempts reached');
                    error.value = "Can't connect to server";
                }
            };
        };

        onMounted(async () => {
            try {
                const { data: teamsData } = await proxy.$http.get(`${serverUrl}/api/client/teams/`);
                const { data: tasksData } = await proxy.$http.get(`${serverUrl}/api/client/tasks/`);
                teams.value = teamsData;
                tasks.value = tasksData;
            } catch (e) {
                console.error('Fetching data:', e);
                error.value = "Can't connect to server";
                return;
            }

            connectWebSocket();
        });

        onBeforeUnmount(() => {
            if (ws.value) {
                ws.value.close();
            }
        });

        return {
            error,
            events,
        };
    },
};
</script>

<style lang="scss" scoped>
.flag {
    color: #00ff00;
    background-color: black;
}

.mark {
    color: #ffff00;
}
</style>
