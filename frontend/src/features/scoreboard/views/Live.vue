<template>
    <div class="screen">
        <live-scoreboard />
    </div>
</template>

<script>
import LiveScoreboard from '../components/LiveScoreboard.vue';

export default {
    components: {
        LiveScoreboard,
    },
};
</script>

<style lang="scss" scoped>
.screen {
    width: 100%;
    height: 100%;
    background-color: black;
}
</style>
