<template>
    <div class="task-page">
        <form-wrapper v-if="task !== null" :submit-callback="submitForm">
            <h2 class="form-title">
                {{ message }}
            </h2>

            <div class="input-group">
                <div class="field full-width">
                    <label>Name:</label>
                    <input v-model="task.name" type="text" placeholder="Task name" />
                </div>

                <div class="field full-width">
                    <label>Checker:</label>
                    <input v-model="task.checker" type="text" placeholder="Checker name" />
                </div>

                <div class="task-row">
                    <div class="field">
                        <label>Gets:</label>
                        <input v-model.number="task.gets" type="number" placeholder="1" />
                    </div>

                    <div class="field">
                        <label>Puts:</label>
                        <input v-model.number="task.puts" type="number" placeholder="1" />
                    </div>

                    <div class="field">
                        <label>Places:</label>
                        <input v-model.number="task.places" type="number" placeholder="1" />
                    </div>
                </div>

                <div class="task-row">
                    <div class="field">
                        <label>Checker timeout:</label>
                        <input v-model.number="task.checker_timeout" type="number" placeholder="10" />
                    </div>

                    <div class="field">
                        <label>Default score:</label>
                        <input v-model.number="task.default_score" type="number" placeholder="2500" />
                    </div>
                </div>

                <div class="field full-width">
                    <label>Checker type:</label>
                    <input v-model="task.checker_type" type="text" placeholder="hackerdom" />
                </div>

                <div class="field full-width">
                    <label>Env path:</label>
                    <input v-model="task.env_path" type="text" placeholder="Environment path" />
                </div>

                <div class="field checkbox-field">
                    <label>
                        <input
                            type="checkbox"
                            :checked="task.active"
                            @input="task.active = $event.target.checked"
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

        const task = ref(null);
        const taskId = ref(null);
        const message = ref(null);

        const updateData = async () => {
            taskId.value = route.params.id;
            if (!taskId.value) {
                task.value = {
                    name: '',
                    checker: '',
                    gets: 1,
                    puts: 1,
                    places: 1,
                    checker_timeout: 10,
                    checker_type: 'hackerdom',
                    env_path: '',
                    default_score: 2500,
                    active: true,
                };
                message.value = 'Creating task';
            } else {
                const { data: taskData } = await proxy.$http.get(
                    `/api/admin/tasks/${taskId.value}`
                );
                task.value = taskData;
                message.value = `Editing task ${task.value.name} (${task.value.id})`;
            }
        };

        const submitForm = async () => {
            if (!taskId.value) {
                const { data: taskData } = await proxy.$http.post(
                    '/api/admin/tasks',
                    task.value
                );
                router.push({ name: 'taskAdmin', params: { id: taskData.id } }).catch(() => {});
            } else {
                const { data: taskData } = await proxy.$http.put(
                    `/api/admin/tasks/${taskId.value}`,
                    task.value
                );
                task.value = taskData;
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
            task,
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
    max-width: 600px;
    width: 100%;
}

.task-page {
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

.task-row {
    display: flex;
    gap: 15px;
    
    .field {
        flex: 1;
    }
}

.field {
    display: flex;
    flex-direction: column;
    gap: 5px;

    label {
        font-size: 15px;
        font-weight: 600;
    }
    
    &.full-width {
        width: 100%;
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

input[type="text"],
input[type="number"] {
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
