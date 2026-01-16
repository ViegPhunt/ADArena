import { defineStore } from 'pinia';

export const useAppStore = defineStore('app', {
    state: () => ({
        showPonies: true,
    }),

    actions: {
        togglePonies() {
            this.showPonies = !this.showPonies;
        },
    },

    persist: true,
});
