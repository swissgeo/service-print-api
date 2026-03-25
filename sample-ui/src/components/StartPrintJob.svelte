<script lang="ts">
    import PrintJob from "./PrintJob.svelte";

    interface StartJobParams {
        format: "a4" | "a3" | "a2" | "a1" | "a0";
        orientation: "portrait" | "landscape";
        resolution: number;
        scale: number;
        view: "print_legend" | "print_map" | "print_vec_map";
        query: string;
    }
    const TARGETS = [
        { alias: "dev", baseUrl: "https://www.dev.sgdi.tech" },
        { alias: "local", baseUrl: "http://localhost:3000" },
    ];

    let target = $state(TARGETS[0]);
    let watchedPrintJobs: Array<StartJobParams> = $state([]);
    let noCache = $state(true);
    let params: StartJobParams = $state({
        format: "a4",
        orientation: "landscape",
        resolution: 96,
        scale: 25000,
        view: "print_map",
        query: "center=2600000%2C1200000&bgLayer=ch.swisstopo.pixelkarte-farbe&topic=ech&layers=ch.meteoschweiz.messwerte-niederschlag-1d%3Bch.astra.wanderland-sperrungen_umleitungen%3Bch.swisstopo.swisstlm3d-wanderwege&z=7",
    });

    async function submit(params: StartJobParams) {
        watchedPrintJobs.push({
            ...params,
            query: `${params.query}${noCache ? `&random=${Math.random()}` : ""}`,
        });
    }
</script>

<div>
    <form>
        <h1>Start Print Job</h1>

        <label>
            Target Stage:
            <select name="target" bind:value={target}>
                {#each TARGETS as t}
                    <option value={t}>{t.alias}</option>
                {/each}
            </select>
            {target.baseUrl}
        </label>

        <label>
            Format:
            <select name="format" bind:value={params.format}>
                {#each ["a4", "a3", "a2", "a1", "a0"] as value}
                    <option {value}>{value.toUpperCase()}</option>
                {/each}
            </select>
        </label>

        <label>
            Orientation:
            <select name="orientation" bind:value={params.orientation}>
                <option value="portrait">Portrait</option>
                <option value="landscape">Landscape</option>
            </select>
        </label>

        <label>
            Resolution:
            <input
                type="number"
                name="resolution"
                bind:value={params.resolution}
                min="1"
            />
        </label>

        <label>
            Scale:
            <input
                type="number"
                name="scale"
                bind:value={params.scale}
                min="1"
            />
        </label>

        <label>
            View:
            <select name="view" bind:value={params.view}>
                <option value="print_legend">Print Legend</option>
                <option value="print_map">Print Map</option>
                <option value="print_vec_map">Print Vec Map</option>
            </select>
        </label>

        <label>
            Query:
            <textarea name="query" bind:value={params.query} rows="4"
            ></textarea>
        </label>

        <label>
            No-Cache:
            <input type="checkbox" name="noCache" bind:checked={noCache} />
        </label>

        <button
            type="submit"
            onclick={(ev) => {
                ev.preventDefault();
                submit(params);
            }}>Submit</button
        >
    </form>
    <div class="print-jobs">
        {#each watchedPrintJobs as job, i}
            <PrintJob
                num={i + 1}
                stage={target.alias}
                baseUrl={target.baseUrl}
                startPrintJobParams={job}
            />
        {/each}
    </div>
</div>

<style>
    div {
        display: flex;
        align-items: start;
    }

    div.print-jobs {
        flex-direction: column;
    }

    form {
        min-width: 30em;
    }
</style>
