<script lang="ts">
    import type { PrintJobStatus } from "./PrintJobStatus";

    let { startPrintJobParams, stage, num } = $props();

    let status: PrintJobStatus | undefined = $state();

    let isLoading = $state(false);

    let error: string | undefined = $state();

    async function startPrintJob() {
        const response = await fetch(`/${stage}/api/print/jobs`, {
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
    }
    startPrintJob();

    async function fetchStatus() {
        isLoading = true;

        const response = await fetch(`/${stage}${status?.reportUrl}`);
        status = await response.json();

        if (status && status.status !== "finished") {
            setTimeout(fetchStatus, 1000);
        }
        isLoading = false;
    }
</script>

<section>
    <aside>
        <h3>Print Job #{num}</h3>
        {#if error}
            <p class="error">{error}</p>
        {/if}
        {#if status}
            <summary>
                {#if status?.status == "started"}Started{/if}
                {#if status?.status == "open"}Open{/if}
                {#if status?.status == "processing"}Processing{/if}
                {#if status?.status == "finished"}Finished{/if}
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
</style>
