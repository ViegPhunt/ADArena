<template>
    <div id="app">
        <header>
            <topbar />
        </header>
        <app-container>
            <slot />
        </app-container>
    </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import AppContainer from '@/components/ui/AppContainer.vue';
import Topbar from '@/components/layout/Topbar.vue';
import { serverUrl } from '@/config';
import { useScoreboardStore } from '@/stores/scoreboard';

export default {
    components: {
        AppContainer,
        Topbar,
    },

    setup() {
        const scoreboardStore = useScoreboardStore();
        const ws = ref(null);
        const reconnectAttempts = ref(0);
        const maxReconnectAttempts = 10;

        const connectWebSocket = () => {
            const wsUrl = serverUrl.replace(/^http/, 'ws');
            ws.value = new WebSocket(`${wsUrl}/api/events/ws/game_events`);

            ws.value.onopen = () => {
                console.log('WebSocket connected to game events');
                reconnectAttempts.value = 0;
            };

            ws.value.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    
                    if (message.event === 'init_scoreboard') {
                        scoreboardStore.handleInitScoreboardMessage(message.data);
                    } else if (message.event === 'update_scoreboard') {
                        scoreboardStore.handleUpdateScoreboardMessage(message.data);
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            ws.value.onerror = (error) => {
                console.error('WebSocket error:', error);
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
                }
            };
        };

        onMounted(() => {
            connectWebSocket();
        });

        onBeforeUnmount(() => {
            if (ws.value) {
                ws.value.close();
            }
        });

        return {};
    },
};
</script>

<style lang="scss" scoped>
#app {
    height: 100%;
    display: flex;

    flex-flow: column nowrap;

    & > :nth-child(2) {
        flex-grow: 1;
    }
}
</style>
