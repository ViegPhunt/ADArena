<template>
    <error-box :error="error">
        <div>
            <p>
                Team
                <b>{{ teamName }}</b>
                ({{ teamId }}) task
                <b>{{ taskName }}</b>
                ({{ taskId }}) history
            </p>
            <div class="table">
                <div class="row">
                    <div class="round">round</div>
                    <div class="status">status</div>
                    <div class="score">score</div>
                    <div class="flags">flags</div>
                    <div class="checks">checks</div>
                    <div class="public">public</div>
                    <div class="private">private</div>
                    <div class="command">command</div>
                </div>
                <div
                    v-for="tt in teamtasks"
                    :key="tt.id"
                    class="row content-row"
                    :style="{
                        backgroundColor: getTeamTaskBackground(tt.status),
                    }"
                >
                    <div class="round">
                        {{ tt.round }}
                    </div>
                    <div class="status">
                        {{ tt.status }}
                    </div>
                    <div class="score">
                        {{ tt.score }}
                    </div>
                    <div class="flags">+{{ tt.stolen }}/-{{ tt.lost }}</div>
                    <div class="checks">
                        {{ tt.checks_passed }}/{{ tt.checks }}
                    </div>
                    <div class="public">
                        {{ tt.public_message }}
                    </div>
                    <div class="private">
                        {{ tt.private_message }}
                    </div>
                    <div class="command">
                        {{ tt.command }}
                    </div>
                </div>
            </div>
        </div>
    </error-box>
</template>

<script>
import { ref, onMounted, getCurrentInstance } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getTeamTaskBackground } from '@/utils/colors';
import ErrorBox from '@/components/ui/ErrorBox.vue';
import '@/assets/styles/tables.scss';

export default {
    components: {
        ErrorBox,
    },

    setup() {
        const route = useRoute();
        const router = useRouter();
        const { proxy } = getCurrentInstance();

        const error = ref(null);
        const taskId = ref(null);
        const teamId = ref(null);
        const teamtasks = ref(null);
        const teamName = ref(null);
        const taskName = ref(null);

        const openTeam = (id) => {
            router.push({ name: 'team', params: { id } }).catch(() => {});
        };

        onMounted(async () => {
            try {
                taskId.value = route.params.taskId;
                teamId.value = route.params.teamId;
                let r = await proxy.$http.get('/api/admin/teamtasks', {
                    params: { team_id: teamId.value, task_id: taskId.value },
                });
                teamtasks.value = r.data;

                const {
                    data: { name: teamNameData },
                } = await proxy.$http.get(`/api/admin/teams/${teamId.value}`);
                teamName.value = teamNameData;

                const {
                    data: { name: taskNameData },
                } = await proxy.$http.get(`/api/admin/tasks/${taskId.value}`);
                taskName.value = taskNameData;
            } catch (e) {
                console.error(e);
                error.value = 'Error occured while fetching data.';
            }
        });

        return {
            error,
            taskId,
            teamId,
            teamtasks,
            teamName,
            taskName,
            getTeamTaskBackground,
            openTeam,
        };
    },
};
</script>

<style lang="scss" scoped>
.row {
    &:first-child {
        font-weight: 700;
    }
}

.content-row {
    & > :not(:first-child) {
        border-left: 1px solid #c6cad1;
    }
}
.round {
    flex: 1 1 0;
    display: flex;
    flex-flow: column nowrap;
    justify-content: center;
}

.status {
    @extend .round;
}

.score {
    @extend .round;
}

.flags {
    @extend .round;
}

.score {
    @extend .round;
}

.checks {
    @extend .round;
}

.public {
    @extend .round;
    flex: 1.5 2 15%;
    overflow-x: auto;
}

.private {
    @extend .public;
}

.command {
    @extend .public;
}
</style>
