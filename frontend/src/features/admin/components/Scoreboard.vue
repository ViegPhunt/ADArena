<template>
    <score-table
        v-if="teams !== null"
        head-row-title="#"
        :team-clickable="true"
        :admin="true"
        :tasks="tasks"
        :teams="teams"
        @openTeam="openTeam"
        @openTeamAdmin="openTeamAdmin"
        @openTaskAdmin="openTaskAdmin"
        @openTeamTaskHistory="openTeamTaskHistory"
    />
</template>

<script>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useScoreboardStore } from '@/stores/scoreboard';
import ScoreTable from '@/components/ui/ScoreTable.vue';

export default {
    components: {
        ScoreTable,
    },

    setup() {
        const router = useRouter();
        const scoreboardStore = useScoreboardStore();

        const tasks = computed(() => scoreboardStore.tasks);
        const teams = computed(() => scoreboardStore.teams);

        const openTeam = (id) => {
            router.push({ name: 'team', params: { id } }).catch(() => {});
        };

        const openTaskAdmin = (id) => {
            router.push({ name: 'taskAdmin', params: { id } }).catch(() => {});
        };

        const openTeamAdmin = (id) => {
            router.push({ name: 'teamAdmin', params: { id } }).catch(() => {});
        };

        const openTeamTaskHistory = (teamId, taskId) => {
            router.push({
                name: 'adminTeamTaskLog',
                params: { teamId, taskId },
            }).catch(() => {});
        };

        return {
            tasks,
            teams,
            openTeam,
            openTaskAdmin,
            openTeamAdmin,
            openTeamTaskHistory,
        };
    },
};
</script>

<style lang="scss" scoped></style>