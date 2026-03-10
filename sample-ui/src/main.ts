import { mount } from "svelte";
import "./app.css";
import App from "./App.svelte";

const app = mount(App, {
  target: document.body.appendChild(document.createElement("main"))!,
});

export default app;
