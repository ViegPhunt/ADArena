<template>
    <div class="team-page">
        <form-wrapper v-if="team !== null" :submit-callback="submitForm">
            <h2 class="form-title">
                {{ message }}
            </h2>

            <div class="input-group">
                <div class="field">
                    <label>Name:</label>
                    <input v-model="team.name" type="text" placeholder="Team name" />
                </div>

                <div class="field">
                    <label>IP Address:</label>
                    <input v-model="team.ip" type="text" placeholder="10.60.x.x" />
                </div>

                <div class="field">
                    <label>Token:</label>
                    <input v-model="team.token" type="text" placeholder="Team token" readonly />
                </div>

                <div class="field checkbox-field">
                    <label>
                        <input
                            type="checkbox"
                            :checked="team.active"
                            @input="team.active = $event.target.checked"
                        />
                        <span>Active</span>
                    </label>
                </div>
            </div>
        </form-wrapper>
    </div>
</template>

<script>
import { ref, watch, onMounted, getCurrentInstance } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import FormWrapper from '@/components/ui/FormWrapper.vue';

export default {
    components: { FormWrapper },

    setup() {
        const route = useRoute();
        const router = useRouter();
        const { proxy } = getCurrentInstance();

        const team = ref(null);
        const teamId = ref(null);
        const message = ref(null);

        const updateData = async () => {
            teamId.value = route.params.id;
            if (!teamId.value) {
                team.value = {
                    name: '',
                    ip: '',
                    token: '',
                    active: true,
                };
                message.value = 'Creating team';
            } else {
                const { data: teamData } = await proxy.$http.get(
                    `/api/admin/teams/${teamId.value}`
                );
                team.value = teamData;
                message.value = `Editing team ${team.value.name} (${team.value.id})`;
            }
        };

        const submitForm = async () => {
            if (!teamId.value) {
                const { data: teamData } = await proxy.$http.post(
                    '/api/admin/teams',
                    team.value
                );
                router.push({ name: 'teamAdmin', params: { id: teamData.id } }).catch(() => {});
            } else {
                const { data: teamData } = await proxy.$http.put(
                    `/api/admin/teams/${teamId.value}`,
                    team.value
                );
                team.value = teamData;
                await updateData();
            }
        };

        watch(() => route.params.id, async () => {
            await updateData();
        });

        onMounted(async () => {
            await updateData();
        });

        return {
            team,
            message,
            submitForm,
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

.team-page {
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

.field {
    display: flex;
    flex-direction: column;
    gap: 5px;

    label {
        font-size: 15px;
        font-weight: 600;
    }
}

.checkbox-field {
    label {
        display: flex;
        align-items: center;
        gap: 10px;
        cursor: pointer;
        font-weight: 600;

        input[type="checkbox"] {
            width: auto;
            margin: 0;
            cursor: pointer;
        }

        span {
            font-size: 15px;
        }
    }
}

input[type="text"] {
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
