<template>
    <component :is="layout">
        <router-view />
    </component>
</template>

<script>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import EmptyLayout from '@/layouts/EmptyLayout.vue';

export default {
    components: {
        DefaultLayout,
        EmptyLayout,
    },
    setup() {
        const route = useRoute();
        
        const layout = computed(() => {
            const layoutName = route.meta.layout || 'default';
            return layoutName === 'empty' ? 'EmptyLayout' : 'DefaultLayout';
        });

        return { layout };
    },
};
</script>

<style lang="scss">
html,
body {
    height: 100%;
    margin: 0;
    background-color: white;
}

body {
    font-family: Arial, system-ui, sans-serif;
}
</style>
