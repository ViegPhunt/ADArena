<template>
    <div class="login-page">
        <form-wrapper :submit-callback="submitCallback">
            <h2 class="form-title">
                Log into the admin panel
            </h2>

            <div class="input-group">
                <input v-model="username" type="text" placeholder="Username" />
                <input v-model="password" type="password" placeholder="Password" />
            </div>
        </form-wrapper>
    </div>
</template>

<script>
import { ref, getCurrentInstance } from 'vue';
import { useRouter } from 'vue-router';
import FormWrapper from '@/components/ui/FormWrapper.vue';

export default {
    components: {
        FormWrapper,
    },

    setup() {
        const router = useRouter();
        const { proxy } = getCurrentInstance();
        
        const username = ref(null);
        const password = ref(null);

        const submitCallback = async () => {
            await proxy.$http.post('/api/admin/auth/login', {
                username: username.value,
                password: password.value,
            });
            router.push({ name: 'admin' }).catch(() => {});
        };

        return {
            username,
            password,
            submitCallback,
        };
    },
};
</script>

<style lang="scss" scoped>
::v-deep form {
    position: relative;
    padding-bottom: 20px;
    max-width: 300px;
    width: 100%;
}

.login-page {
    margin: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.form-title {
    margin-bottom: 24px;
    font-size: 24px;
    font-weight: 700;
    color: #000;
    text-align: center;
}

.input-group {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

input {
    width: 100%;
    padding: 12px 16px;
    font-size: 15px;
    color: #000;
    background-color: #fff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    outline: none;
    transition: all 0.2s ease-in-out;
    box-sizing: border-box;

    &::placeholder {
        color: #9ca3af;
    }
}

::v-deep input[type="submit"] {
    width: 100%;
    margin-top: 15px !important;
    padding: 12px 16px;
    background-color: #2196F3 !important;
    color: #fff;
    font-weight: 600;
    font-size: 15px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: background-color 0.2s ease-in-out;

    &:hover {
        background-color: #64B5F6 !important;
    }
}
</style>
