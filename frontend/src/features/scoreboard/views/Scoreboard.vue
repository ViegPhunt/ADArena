<template>
    <div class="scoreboard">
        <scoreboard />
    </div>
</template>

<script>
import Scoreboard from '../components/Scoreboard.vue';

export default {
    components: {
        Scoreboard,
    },
};
</script>

<style lang="scss" scoped>
.scoreboard {
    margin-top: 2em;
}
</style>