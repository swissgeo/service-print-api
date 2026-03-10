<script lang="ts">
    import type { PrintJobStatus } from "./PrintJobStatus";

    let { stage, statusUrl } = $props();

    let status: PrintJobStatus | undefined = $state();

    let isLoading = $state(false);

    async function fetchStatus() {
        isLoading = true;

        const response = await fetch(`/${stage}/${statusUrl}`);
        status = await response.json();

        if (status && status.status === "finished") {
            clearInterval(intervalId);
        }
        isLoading = false;
    }

    fetchStatus();
    const intervalId = setInterval(fetchStatus, 5000);
</script>

<section>
    <aside>
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
