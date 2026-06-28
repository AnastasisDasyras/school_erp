import { createRouter, createWebHistory } from "vue-router";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/students",
    },
    {
      path: "/students",
      name: "students",
      component: () => import("@/views/StudentsView.vue"),
    },
  ],
});
