<template>
    <form @submit.prevent="handleSubmit">
        <p>{{ title }}</p>
        <slot />
        <input type="submit" value="Submit" />
        <p v-if="error !== null" class="error-message">
            {{ error }}
        </p>
    </form>
</template>

<script>
export default {
    props: {
        title: {
            type: String,
            required: true,
        },
        submitCallback: {
            type: Function,
            required: true,
        },
    },

    data: function () {
        return {
            error: null,
        };
    },

    methods: {
        handleSubmit: async function () {
            try {
                await this.submitCallback();
            } catch (e) {
                console.error(e);
                this.error = e;
            }
        },
    },
};
</script>

<style lang="scss" scoped>
.error-message {
    position: absolute;
    top: 100%;
    left: 0;
    width: 100%;
    text-align: center;
    margin: 0;
    color: red;
    font-size: 14px;
    font-weight: 500;
}

</style>
