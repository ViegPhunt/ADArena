<template>
    <div v-if="error !== null">
        {{ error }}
    </div>
    <div v-else-if="team !== null" class="table">
        <div class="row">
            <div class="team">Team</div>
            <div class="score">Score</div>
            <div class="service-name">
                <div v-for="{ name } in tasks" :key="name" class="service-cell">
                    {{ name }}
                </div>
            </div>
        </div>
        <div>
            <div v-for="(state, index) in states" :key="index" class="row">
                <div class="team">
                    <div class="team-name">
                        {{ team.name }}
                    </div>
                    <div class="ip">
                        {{ team.ip }}
                    </div>
                </div>
                <div class="score">
                    {{ state.score.toFixed(2) }}
                </div>
                <div class="service">
                    <div
                        v-for="(
                            { sla, score, stolen, lost, message, status }, i
                        ) in state.tasks"
                        :key="i"
                        class="service-cell"
                        :style="{
                            fontSize: `${1 - tasks.length / 20}em`,
                            backgroundColor: getTeamTaskBackground(status),
                        }"
                        v-tooltip="{
                            content: message,
                            placement: 'top',
                        }"
                    >
                        <div class="sla">
                            <i class="fa-solid fa-heart-pulse"></i> : {{ sla.toFixed(2) }}%
                        </div>
                        <div class="fp">
                            <i class="fa-solid fa-star"></i> : {{ score.toFixed(2) }}
                        </div>
                        <div class="flags">
                            <i class="fa-solid fa-bolt-lightning"></i> : {{ stolen }} / <i class="fa-solid fa-shield-halved"></i> : {{ lost }}
                        </div>
                        <div class="status-text">
                            <i class="fa-solid fa-circle-info"></i> : {{ getStatusName(status) }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, onMounted, getCurrentInstance } from 'vue';
import { useRoute } from 'vue-router';
import { useScoreboardStore } from '@/stores/scoreboard';
import { getTeamTaskBackground } from '@/utils/colors';
import { statusesNames } from '@/config';
import Task from '@/models/task';
import TeamTask from '@/models/teamTask';
import '@/assets/tables.scss';

export default {
    setup() {
        const route = useRoute();
        const { proxy } = getCurrentInstance();
        const scoreboardStore = useScoreboardStore();

        const error = ref(null);
        const team = ref(null);
        const teamId = ref(null);
        const tasks = ref(null);
        const round = ref(0);
        const states = ref([]);

        const getStatusName = (status) => {
            return statusesNames[status]?.toLowerCase();
        };

        onMounted(async () => {
            teamId.value = route.params.id;
            try {
                const { data: teams } = await proxy.$http.get('/api/client/teams/');
                const { data: tasksData } = await proxy.$http.get('/api/client/tasks/');
                let { data: statesData } = await proxy.$http.get(
                    `/api/client/teams/${teamId.value}/`
                );
                team.value = teams.filter(({ id }) => id == teamId.value)[0];
                tasks.value = tasksData.map((task) => new Task(task)).sort(Task.comp);
                round.value = scoreboardStore.round ?? 0;

                statesData = statesData.map((x) => ({
                    id: Number(x.id),
                    round: Number(x.round),
                    task_id: Number(x.task_id),
                    team_id: Number(x.team_id),
                    status: x.status,
                    stolen: x.stolen,
                    lost: x.lost,
                    score: Number(x.score),
                    checks: Number(x.checks),
                    checks_passed: Number(x.checks_passed),
                    timestamp_secs: Number(
                        x.timestamp.slice(0, x.timestamp.indexOf('-'))
                    ),
                    timestamp_num: Number(
                        x.timestamp.slice(x.timestamp.indexOf('-') + 1)
                    ),
                    message: x.message,
                }));

                statesData = statesData.sort(
                    (
                        { timestamp_secs: tss1, timestamp_num: tsn1 },
                        { timestamp_secs: tss2, timestamp_num: tsn2 }
                    ) => {
                        if (tss1 === tss2) {
                            return tsn2 - tsn1;
                        }
                        return tss2 - tss1;
                    }
                );

                statesData = statesData.map((state) => new TeamTask(state));
                const byTask = {};
                for (const state of statesData) {
                    let key = state.taskId - 1;
                    if (!byTask[key]) {
                        byTask[key] = [];
                    }
                    byTask[key].push(state);
                }
                const byTaskArray = Object.values(byTask);
                let rowCount = Math.min(...byTaskArray.map((x) => x.length));

                states.value = [];
                for (let i = 0; i < rowCount; i += 1) {
                    states.value.push({
                        tasks: byTaskArray.map((x) => x[i]),
                        score: byTaskArray
                            .map((x) => x[i])
                            .reduce(
                                (acc, { score, sla }) =>
                                    acc + (score * sla) / 100.0,
                                0
                            ),
                    });
                }
            } catch (e) {
                error.value = "Can't connect to server";
            }
        });

        return {
            error,
            team,
            tasks,
            states,
            getTeamTaskBackground,
            getStatusName,
        };
    },
};
</script>

<style lang="scss" scoped>
.team-name {
    font-weight: bold;
}

.number {
    flex: 1 1 0;
    display: flex;
    flex-flow: column nowrap;
    justify-content: center;
}

.team {
    flex: 4 1 15%;
    display: flex;
    flex-flow: column nowrap;
    justify-content: center;
    position: relative;
}

.score {
    flex: 2 1 5%;
    display: flex;
    flex-flow: column nowrap;
    justify-content: center;
}

.service {
    flex: 20 2 0;
    display: flex;
    flex-flow: row nowrap;

    border-left: 1px solid #c6cad1;

    & > :not(:last-child) {
        border-right: 1px solid #c6cad1;
    }
}

.service-name {
    flex: 20 2 0;
    display: flex;
    flex-flow: row nowrap;
    text-align: center;
    font-weight: bold;
}

.service-cell {
    flex: 1 1 0;

    position: relative;

    display: flex;
    flex-flow: column nowrap;
    justify-content: space-around;
}

.sla {
    text-align: left;
    margin-left: 0.5em;
}

.fp {
    text-align: left;
    margin-left: 0.5em;
}

.flags {
    text-align: left;
    margin-left: 0.5em;
}

.status-text {
    text-align: left;
    margin-left: 0.5em;
}
</style>

<style>
.tooltip {
    display: block !important;
    z-index: 10000;

    .tooltip-inner {
        background: black;
        color: white;
        border-radius: 0.5em;
        padding: 0.75em 1em;
        font-size: 0.85em;
        max-width: 300px;
    }

    .tooltip-arrow {
        width: 0;
        height: 0;
        border-style: solid;
        position: absolute;
        margin: 5px;
        border-color: black;
        z-index: 1;
    }

    &[x-placement^="top"] {
        margin-bottom: 5px;

        .tooltip-arrow {
            border-width: 5px 5px 0 5px;
            border-left-color: transparent !important;
            border-right-color: transparent !important;
            border-bottom-color: transparent !important;
            bottom: -5px;
            left: calc(50% - 5px);
            margin-top: 0;
            margin-bottom: 0;
        }
    }

    &[aria-hidden='true'] {
        visibility: hidden;
        opacity: 0;
        transition: opacity 0.15s, visibility 0.15s;
    }

    &[aria-hidden='false'] {
        visibility: visible;
        opacity: 1;
        transition: opacity 0.15s;
    }
}
</style>