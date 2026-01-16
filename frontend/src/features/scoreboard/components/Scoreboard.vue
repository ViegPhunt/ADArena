<template>
    <score-table
        v-if="teams !== null"
        head-row-title="#"
        :team-clickable="true"
        :tasks="tasks"
        :teams="teams"
        @openTeam="openTeam"
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

        const teams = computed(() => scoreboardStore.teams);
        const tasks = computed(() => scoreboardStore.tasks);

        const openTeam = (id) => {
            router.push({ name: 'team', params: { id } }).catch(() => {});
        };

        return { teams, tasks, openTeam };
    },
};
</script>

<style lang="scss" scoped></style>
