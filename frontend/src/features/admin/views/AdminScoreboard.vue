<template>
    <div>
        <div class="create-group">
            <button class="create-btn" @click="createTask">Create task</button>
            <button class="create-btn" @click="createTeam">Create team</button>
        </div>
        <scoreboard />
    </div>
</template>

<script>
import { useRouter } from 'vue-router';
import Scoreboard from '../components/Scoreboard.vue';

export default {
    components: {
        Scoreboard,
    },

    setup() {
        const router = useRouter();

        const createTask = () => {
            router.push({ name: 'createTask' }).catch(() => {});
        };

        const createTeam = () => {
            router.push({ name: 'createTeam' }).catch(() => {});
        };

        return { createTask, createTeam };
    },
};
</script>

<style lang="scss" scoped>
.create-group {
    display: flex;
    flex-flow: row-reverse;
}

.create-btn {
    font-size: 1em;
    margin: 1em;
}
</style>
