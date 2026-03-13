<script lang="ts">
    import type { PrintJobStatus } from "./PrintJobStatus";

    let { startPrintJobParams, stage, baseUrl, num } = $props();

    let status: PrintJobStatus | undefined = $state();

    let isLoading = $state(false);

    let error: string | undefined = $state();
    let start = $state(Date.now());
    let now = $state(Date.now());
    let elapsed = $derived(start ? now - start : 0);

    const ticker = setInterval(() => {
        now = Date.now();
    }, 1000);
    $effect(() => () => clearInterval(ticker));

    const isRunning = $derived(
        status?.status !== "finished" && status?.status !== "error",
    );

    async function startPrintJob() {
        try {
            const url = baseUrl ? `${baseUrl}/api/print/jobs` : `/${stage}/api/print/jobs`;
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(startPrintJobParams),
            });
            if (response.ok) {
                status = await response.json();
                setTimeout(fetchStatus, 1000);
            } else {
                error = `HTTP ${response.status}: ${await response.text()}`;
                console.error(error);
            }
        } catch (e) {
            error = e instanceof Error ? e.message : String(e);
            console.error(error);
            clearInterval(ticker);
        }
    }
    startPrintJob();

    async function fetchStatus() {
        isLoading = true;

        const response = await fetch(baseUrl ? `${baseUrl}${status?.reportUrl}` : `/${stage}${status?.reportUrl}`);
        status = await response.json();

        if (status && status.status !== "finished") {
            setTimeout(fetchStatus, 1000);
        } else {
            clearInterval(ticker);
            now = Date.now();
        }
        isLoading = false;
    }
</script>

<section>
    <aside>
        <h3>
            {#if isRunning}
                <img class="icon" src="spinner.svg" alt="Loading..." />
            {/if}
            Print Job #{num}
            <small>({status?.status} - {elapsed}ms)</small>
        </h3>
        {#if error}
            <p class="error">{error}</p>
        {/if}
        {#if status}
            <summary>
                {#if status?.pdfUrl}<a href={status?.pdfUrl} target="_blank"
                        >Download PDF</a
                    >{/if}
                <details>
                    <dl>
                        <dt>Status</dt>
                        <dd>{status?.status}</dd>
                        <dt>Message</dt>
                        <dd>{status?.message}</dd>
                        <dt>Report URL</dt>
                        <dd>{status?.reportUrl}</dd>
                        <dt>Created</dt>
                        <dd>{status?.created}</dd>
                        <dt>Finished</dt>
                        <dd>{status?.finished}</dd>
                        <dt>Started</dt>
                        <dd>{status?.started}</dd>
                    </dl>
                </details>
            </summary>
        {/if}
    </aside>
</section>

<style>
    .error {
        color: red;
        text-overflow: ellipsis;
        max-height: 3em;
        overflow: hidden;
    }

    .icon {
        width: 1.5em;
        height: 1.5em;
        animation: rotation 2s infinite linear;
    }

    dt {
        font-weight: bold;
    }

    dd {
        margin-left: 0.5em;
        margin-bottom: 0.3em;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    @keyframes rotation {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
</style>
