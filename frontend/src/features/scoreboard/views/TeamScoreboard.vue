<template>
    <div class="team-scoreboard">
        <team-scoreboard />
    </div>
</template>

<script>
import TeamScoreboard from '../components/TeamScoreboard.vue';

export default {
    components: {
        TeamScoreboard,
    },
};
</script>

<style lang="scss" scoped>
.team-scoreboard {
    margin-top: 2em;
}
</style>