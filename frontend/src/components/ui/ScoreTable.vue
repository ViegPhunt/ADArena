<template>
    <div class="table">
        <div class="row">
            <div class="team-group">
                <div class="number">
                    {{ headRowTitle }}
                </div>
                <div class="team">Team</div>
                <div class="score">Score</div>
            </div>
            <div class="service-name">
                <div
                    v-for="{ name, id } in tasks"
                    :key="name"
                    :style="taskStyle"
                    class="service-cell"
                    @click="$emit('openTask', id)"
                >
                    {{ name }}
                    <button
                        v-if="admin"
                        class="edit"
                        @click="$emit('openTaskAdmin', id)"
                    >
                        <i class="fas fa-edit" />
                    </button>
                </div>
            </div>
        </div>
        <transition-group name="teams-list">
            <div
                v-for="(
                    {
                        name,
                        score: totalScore,
                        tasks: teamTasks,
                        ip,
                        id,
                    },
                    index
                ) in teams"
                :key="name"
                class="row"
            >
                <div class="team-group pd-3">
                    <div
                        class="number"
                    >
                        {{ index + 1 }}
                    </div>
                    <div
                        class="team team-row"
                        :style="teamStyle"
                        @click="$emit('openTeam', id)"
                    >
                        <div class="team-name">
                            {{ name }}
                        </div>
                        <div class="ip">
                            {{ ip }}
                        </div>
                        <button
                            v-if="admin"
                            class="edit"
                            @click="$emit('openTeamAdmin', id)"
                            @click.stop
                        >
                            <i class="fas fa-edit" />
                        </button>
                    </div>
                    <div
                        class="score"
                    >
                        {{ totalScore.toFixed(2) }}
                    </div>
                </div>
                <div class="service">
                    <div
                        v-for="{
                            id: teamTaskID,
                            teamId,
                            taskId,
                            sla,
                            score,
                            stolen,
                            lost,
                            message,
                            status,
                        } in teamTasks"
                        :key="teamTaskID"
                        class="service-cell"
                        :style="{
                            fontSize: `${1 - teamTasks.length / 20}em`,
                            backgroundColor: getTeamTaskBackground(status),
                        }"
                        v-tooltip="{
                            content: message,
                            placement: 'top',
                        }"
                    >
                        <button
                            v-if="admin"
                            class="tt-edit"
                            @click="
                                $emit('openTeamTaskHistory', teamId, taskId)
                            "
                        >
                            <i class="fas fa-edit" />
                        </button>
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
        </transition-group>
    </div>
</template>

<script>
import { getTeamTaskBackground } from '@/utils/colors';
import { statusesNames } from '@/config';
import '@/assets/tables.scss';

export default {
    props: {
        headRowTitle: {
            type: String,
            default: '#',
        },
        tasks: {
            type: Array,
            required: true,
        },
        teams: {
            type: Array,
            required: true,
        },
        teamClickable: Boolean,
        taskClickable: Boolean,
        admin: Boolean,
    },

    data: function () {
        return {
            getTeamTaskBackground,
            statusesNames,
        };
    },

    computed: {
        teamStyle: function () {
            return this.teamClickable
                ? {
                      cursor: 'pointer',
                  }
                : {};
        },

        taskStyle: function () {
            return this.taskClickable
                ? {
                      cursor: 'pointer',
                  }
                : {};
        },
    },

    methods: {
        getStatusName(status) {
            return this.statusesNames[status]?.toLowerCase();
        },
    },
};
</script>

<style lang="scss" scoped>
.pd-3 {
    margin-left: 2px;
}

.team-group {
    flex: 7 1 20%;
    display: flex;
    flex-flow: row nowrap;
}

.teams-list-move {
    transition: transform 1s;
}

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

.edit {
    padding: 0;
    position: absolute;
    top: 0.5em;
    left: calc(100% - 2.5em - 0.5em);
    width: 2.5em;
    height: 2.5em;

    border-radius: 0.3em;
    font-size: 0.7em;
    border: 1px solid #c6cad1;

    &:focus {
        outline: 0;
        border: 1px solid #c6cad1;
    }
}

.tt-edit {
    @extend .edit;
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