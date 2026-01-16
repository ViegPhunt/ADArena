import { defineStore } from 'pinia';
import axios from 'axios';
import Team from '@/models/team';
import Task from '@/models/task';
import TeamTask from '@/models/teamTask';

export const useScoreboardStore = defineStore('scoreboard', {
    state: () => ({
        round: 0,
        roundTime: null,
        maxRound: null,
        roundStart: null,
        roundProgress: null,
        teams: null,
        tasks: null,
        teamTasks: null,
    }),

    getters: {
        sortedTeams: (state) => {
            return state.teams ? [...state.teams].sort(Team.comp) : [];
        },
        sortedTasks: (state) => {
            return state.tasks ? [...state.tasks].sort(Task.comp) : [];
        },
    },

    actions: {
        setRound(round) {
            this.round = round;
        },

        setRoundStart(roundStart) {
            this.roundStart = roundStart;
        },

        setRoundTime(roundTime) {
            this.roundTime = roundTime;
        },

        setMaxRound(maxRound) {
            this.maxRound = maxRound;
        },

        setRoundProgress(roundProgress) {
            this.roundProgress = roundProgress;
        },

        setTeams(teams) {
            this.teams = teams;
        },

        setTasks(tasks) {
            this.tasks = tasks;
        },

        setGameState(payload) {
            this.round = payload.round;
            this.roundStart = payload.roundStart;
            this.teamTasks = payload.teamTasks;
        },

        updateTeams() {
            if (this.teams !== null) {
                this.teams.forEach((team) => {
                    team.update(this.teamTasks);
                });
                this.teams = this.teams.sort(Team.comp);
            }
        },

        async fetchRoundTime() {
            try {
                const response = await axios.get('/client/config/');
                const { round_time: roundTime, max_round: maxRound, round } = response.data;
                this.setRoundTime(roundTime);
                this.setMaxRound(maxRound);
                if (round !== null && round >= 0) {
                    this.setRound(round);
                }
            } catch (error) {
                console.error('Failed to fetch round time:', error);
            }
        },

        calculateRoundProgress() {
            const { round, roundTime, roundStart } = this;
            if (roundTime === null || roundStart === null || round < 1) {
                this.setRoundProgress(null);
                return;
            }
            let roundProgress = (new Date().getTime() / 1000 - roundStart) / roundTime;
            roundProgress = Math.min(Math.max(roundProgress, 0), 1);
            roundProgress = Math.floor(roundProgress * 100);
            this.setRoundProgress(roundProgress);
        },

        handleUpdateScoreboardMessage(payload) {
            let { round, round_start: roundStart, team_tasks: teamTasks } = payload;

            teamTasks = teamTasks.map((tt) => new TeamTask(tt));
            const state = { round, roundStart, teamTasks };

            this.setGameState(state);
            this.updateTeams();
        },

        handleInitScoreboardMessage(payload) {
            let { state, teams, tasks } = payload;

            tasks = tasks.map((task) => new Task(task)).sort(Task.comp);
            this.setTasks(tasks);
            this.handleUpdateScoreboardMessage(state);

            teams = teams
                .map(
                    (team) =>
                        new Team({
                            teamTasks: this.teamTasks,
                            tasks: this.tasks,
                            ...team,
                        })
                )
                .sort(Team.comp);

            this.setTeams(teams);
        },
    },
});
