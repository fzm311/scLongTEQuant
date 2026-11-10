# scLongTEQuant

**Systematic benchmarking and reproducible workflows for isoform and transposable element quantification in single-cell long-read transcriptomics**

## Overview

`scLongTEQuant` is a resource for benchmarking and recommending analysis strategies for transposable element (TE)-derived and TE-associated transcripts in single-cell long-read RNA-seq data, including PacBio and Oxford Nanopore Technologies (ONT) data. The project evaluates multiple tools that generate quantification matrices from long-read RNA-seq data and uses companion in-house scripts to classify the resulting matrices into distinct transcript categories:

- **Gene-alone** transcripts;
- **TE-alone** transcripts;
- **TE–Gene chimeric** transcripts.

The classified results are further aggregated and quantified at both the **TE locus level** and the **TE subfamily level**. Based on the benchmarking results, `scLongTEQuant` provides a step-wise recommendation scheme for tool selection and analysis strategy, together with reproducible scripts and configuration files.

## Project Positioning

`scLongTEQuant` is positioned as a **benchmarking resource, a step-wise workflow recommendation guide, and a reproducible script collection**, rather than a single new quantification algorithm or standalone software tool. The project does not bind itself to any single quantification tool; Instead, it recommends suitable tool combinations for different analysis steps according to the analysis objective and data characteristics, and provides guidance on their use.

## Key Features

- Benchmarking of multiple tools that generate quantification matrices from single-cell long-read RNA-seq data;
- Unified classification of tool-derived matrices into Gene-alone, TE-alone, and TE–Gene chimeric transcripts;
- Quantification at the TE locus level;
- Quantification at the TE subfamily level;
- Comparative evaluation of TE detection, transcript classification, quantification consistency, and aggregation results;
- Step-wise recommendations for tool selection across the analysis workflow;
- Reproducible scripts, configuration files, and summary tables for benchmarking and downstream analysis.

## Recommended Workflow Overview
![](./scLongTEQuant-pipeline.png)

![The recommended workflow](./scLongTEQuant-recommend.png)

## Installation of Recommended Tools

The commands below target a Linux environment. Create a working directory and substitute `path/to/` with the corresponding local path. Versions are those used in the benchmark.

### Prerequisites

Install a Conda distribution such as [Miniforge](https://github.com/conda-forge/miniforge) before creating the environments below. Five additional components are required alongside FLAMESv2, LRAA, wf-single-cell, and Bambu-pipe.

#### Java and Nextflow

[wf-single-cell](https://github.com/epi2me-labs/wf-single-cell) v3.3.4 requires Nextflow >= 23.04.2. [Bambu-pipe](https://github.com/GoekeLab/bambu-pipe) v0.9.1 requires Nextflow >= 26.04.0. The commands below install Nextflow 26.04.4. Nextflow requires Bash >= 3.2 and Java 17–26 ([installation guide](https://docs.seqera.io/nextflow/install)). `NXF_VER` selects that release when the launcher runs, so keep it set in each shell that executes Nextflow.

```bash
conda install -y -c conda-forge openjdk=17
export NXF_VER=26.04.4
curl -s https://get.nextflow.io | bash
chmod +x nextflow
mkdir -p "$HOME/.local/bin"
mv nextflow "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
nextflow info
```

#### Singularity

FLAMESv2 is distributed as a Singularity image, and wf-single-cell and Bambu-pipe run under the Singularity profile. On an HPC system, load the site module that provides the `singularity` command:

```bash
module load singularity
```

On a standalone Linux system, install [Apptainer](https://apptainer.org/docs/admin/main/installation.html), which provides the same command-line interface. The image used for FLAMESv2 is retrieved with:

```bash
singularity pull path/to/flames.sif docker://ghcr.io/mritchielab/flames:20af1ce
```

This image corresponds to the container documented for [FLAMES](https://github.com/mritchielab/FLAMES) at commit `20af1ce`.

#### fastplong 0.4.1

[fastplong](https://github.com/OpenGene/fastplong) v0.4.1 performs quality control for both PacBio and ONT reads. The Bioconda recipe is the installation route given in the v0.4.1 documentation.

```bash
conda create -n fastplong -y -c bioconda -c conda-forge fastplong=0.4.1
conda activate fastplong
fastplong --help
```

#### miniTEQuant

[miniTEQuant](https://github.com/calm109/miniTEQuant) builds the TE annotation and calculates TE-locus, TE-subfamily, and transcript-class results.

```bash
git clone https://github.com/calm109/miniTEQuant.git path/to/miniTEQuant
cd path/to/miniTEQuant
conda env create -f environment.yml
conda activate miniTEQuant
```

The upstream installation additionally provides minimap2, flexiplex, and nailpolish for analyses in which miniTEQuant itself demultiplexes, aligns, and quantifies reads. In the workflow recommended here those operations are performed by wf-single-cell and FLAMESv2, so the environment created above is sufficient for `create_simple_TE_gtf.py` and `cal_TE`.

#### RepeatMasker

[RepeatMasker](https://www.repeatmasker.org/RepeatMasker/) 4.2.4 screens `path/to/genome.fa` and writes the annotation table that miniTEQuant converts to a TE GTF. The Bioconda package installs RMBlast, TRF, HMMER, and FamDB 3.0.0. RepeatMasker 4.2.4 does not include the Dfam sequences. Download the Dfam 4.0 root partition and the curated consensus partition into the FamDB data directory. RMBlast searches those consensus sequences.

With `channel_priority: strict`, the channel order `-c bioconda -c conda-forge` cannot solve this specification. `--override-channels` uses only the two channels named in the command and leaves the user's conda configuration unchanged.

```bash
conda create -n repeatmasker -y --override-channels -c conda-forge -c bioconda repeatmasker=4.2.4 famdb=3.0.0
conda activate repeatmasker
FDB_DIR="$(conda info --base)/envs/repeatmasker/share/famdb-3.0.0/Libraries/famdb"
mkdir -p "$FDB_DIR"
curl -fsSL -o "$FDB_DIR/dfam40.0.h5.gz" \
    https://www.dfam.org/releases/Dfam_4.0/families/FamDB/dfam40.0.h5.gz
curl -fsSL -o "$FDB_DIR/dfam40.curated.consensus.0.h5.gz" \
    https://www.dfam.org/releases/Dfam_4.0/families/FamDB/dfam40.curated.consensus.0.h5.gz
gunzip -f "$FDB_DIR/dfam40.0.h5.gz" "$FDB_DIR/dfam40.curated.consensus.0.h5.gz"
famdb.py info
```

### FLAMESv2

Pull the Singularity image shown in [Prerequisites](#singularity). The image already contains the FLAMES R package, flexiplex, minimap2, samtools, and Oarfish used by `SingleCellPipeline`. Enter the image to confirm that the package loads:

```bash
singularity exec -e path/to/flames.sif Rscript -e 'library(FLAMES); packageVersion("FLAMES")'
```

Documentation: [mritchielab/FLAMES](https://github.com/mritchielab/FLAMES) and the [single-cell pipeline reference](https://mritchielab.github.io/FLAMES/reference/SingleCellPipeline.html).

### LRAA 0.15.0

[LRAA](https://github.com/MethodsDev/LongReadAlignmentAssembler) v0.15.0 is used for reference-guided novel-isoform discovery. The tagged release contains the `LRAA` executable. Its Python and alignment dependencies are installed in a dedicated environment.

```bash
wget https://github.com/MethodsDev/LongReadAlignmentAssembler/archive/refs/tags/LRAA_v0.15.0.tar.gz
tar -xzvf LRAA_v0.15.0.tar.gz
cd path/to/LongReadAlignmentAssembler-LRAA_v0.15.0  
chmod +x LRAA
export PATH="path/to/LongReadAlignmentAssembler-LRAA_v0.15.0:$PATH"

conda create -n lraa -y python=3.10
conda activate lraa
conda install -y -c bioconda -c conda-forge samtools pysam gffcompare
conda install -y -c conda-forge python-igraph leidenalg tqdm
pip install pandas scipy numpy psutil lmdb
```

Further usage is described in the [LRAA wiki](https://github.com/MethodsDev/LongReadAlignmentAssembler/wiki). For single-cell BAMs produced by this workflow, cell barcodes and UMIs are stored in the `CB` and `UB` tags.

### wf-single-cell 3.3.4

wf-single-cell is executed remotely by Nextflow; a separate compilation step is not required. Retrieve release v3.3.4 and inspect its parameters:

```bash
nextflow pull epi2me-labs/wf-single-cell -r v3.3.4
export NXF_SYNTAX_PARSER=v1
nextflow run epi2me-labs/wf-single-cell -r v3.3.4 --help
```

Nextflow 26.04.4 defaults to syntax parser v2. wf-single-cell 3.3.4 begins with `import groovy.json.JsonBuilder`, which that parser rejects, so set `NXF_SYNTAX_PARSER=v1` in every shell that runs it. Keep `NXF_VER=26.04.4`; do not move this workflow to a newer Nextflow release. The pulled asset stays on revision v3.3.4. `nextflow run` without `-r v3.3.4` stops with `stuck on revision: v3.3.4`. After the asset is present, also set `NXF_OFFLINE=true`. Without it, Nextflow can wait indefinitely while it checks GitHub for another revision.

When `-profile singularity` is set, the workflow would normally download its own containers. In this project, however, the two required Singularity image files, `wf-single-cell.sif` and `wf-common.sif`, are included and were obtained from the official source. Therefore, before executing the workflow, edit the Nextflow configuration file generated by the pull step:

```bash
.nextflow/assets/epi2me-labs/wf-single-cell/nextflow.config
```

In the `process` block located below the comment `// other profiles may override.`, replace the container specifications `ontresearch/wf-single-cell:${params.wf.container_sha}` and `ontresearch/wf-common:${params.wf.common_sha}` with the absolute paths to `wf-single-cell.sif` and `wf-common.sif`, respectively. The absolute paths can be obtained with `realpath`; replace the placeholders below with the actual paths on the local system:

```groovy
// other profiles may override.
process {
    withLabel:singlecell {
        container = "/absolute/path/to/wf-single-cell.sif"
    }
    withLabel:wf_common {
        container = "/absolute/path/to/wf-common.sif"
    }
    withLabel:ctat_lr_fusion {
        container = "trinityctat/ctat_lr_fusion:1.1.0"
    }
    shell = ['/bin/bash', '-euo', 'pipefail']
}
```

The `ctat_lr_fusion` container specification and the `shell` directive remain unchanged. The reference directory must follow the 10x layout documented by [epi2me-labs/wf-single-cell](https://github.com/epi2me-labs/wf-single-cell): `path/to/ref_genome_dir/fasta/genome.fa` and `path/to/ref_genome_dir/genes/genes.gtf`. These two files are `path/to/genome.fa` and `path/to/genes.gtf`.

Note: `nextflow pull` may regenerate or overwrite the contents under `.nextflow/assets`; therefore, the modification to `nextflow.config` must be applied after the pull step. If the workflow is pulled again or the release version is changed, the modification should be reapplied.

### Bambu-pipe 0.9.1

Clone the v0.9.1 release of [Bambu-pipe](https://github.com/GoekeLab/bambu-pipe).

```bash
wget https://github.com/GoekeLab/bambu-pipe/archive/refs/tags/v0.9.1.tar.gz
tar -xzvf v0.9.1.tar.gz
cd path/to/bambu-pipe-0.9.1
nextflow config main.nf
```

`nextflow run main.nf --help` fails because v0.9.1 does not declare a `help` parameter. `nextflow config main.nf` prints the parameters.

Software dependencies are the Singularity images declared in `conf/containers.config`. With `-profile singularity`, Nextflow sets `singularity.enabled = true` and `singularity.autoMounts = true`, and pulls each image itself the first time the corresponding process runs. Pulled images are cached by Nextflow and reused on later runs. The profile also binds the working directory with `--bind ${PWD}`.

| Process label | Image | Used for |
| --- | --- | --- |
| `r` | `ghcr.io/ch99l/bambu-pipe-r:latest` | Bambu R package: annotation preparation, transcript discovery, and quantification |
| `spaceranger` | `quay.io/nf-core/spaceranger:9c5e7dc93c32448e` | Barcode and spatial-coordinate extraction |
| `minimap2_samtools` | `community.wave.seqera.io/library/minimap2_samtools:b09096fc890429ce` | Genome index and alignment |
| `preprocess` | `community.wave.seqera.io/library/chopper_cutadapt_flexiplex_pigz:077c3bc67452482c` | FASTQ preprocessing with chopper, cutadapt, flexiplex, and pigz |

Run the pipeline with `-profile singularity`. On a local machine add `,local`; on Slurm add `,hpc`, as described in the repository README.

## Input Files

Paths below are generic. A file that reappears in a later command is written with the same name.

| File | Role |
| --- | --- |
| `path/to/reads.fastq.gz` | Platform-specific long-read FASTQ. Plain `.fastq`, `.fq`, and gzip-compressed files are accepted. |
| `path/to/reads_filtered.fastq.gz` | Reads retained by fastplong, together with `path/to/reads_filtered_report.html` and `path/to/reads_filtered_report.json`. |
| `path/to/genome.fa` | Reference genome FASTA. |
| `path/to/genes.gtf` | Reference gene annotation in GTF format. |
| `path/to/ref_genome_dir` | 10x-style reference directory for wf-single-cell, containing `fasta/genome.fa` and `genes/genes.gtf`. |
| `path/to/barcodes.txt` | Cell-barcode whitelist, one barcode per line. Decompress a gzipped whitelist before use. |
| `path/to/tagged.bam` | Coordinate-sorted BAM that already carries cell-barcode and UMI tags. This is either the starting file, when both tags are already present, or the alignment written by wf-single-cell (`<sample>/<sample>.tagged.bam`). |
| `path/to/align2genome.bam` | Genome alignment written by FLAMESv2 for PacBio reads, with cell barcodes in `CB` and UMIs in `UB`. |
| `path/to/samplesheet.csv` | ONT Bambu-pipe sample sheet. The header is `sample,path,chemistry,technology`, and `path` points to `path/to/tagged.bam`. |
| `path/to/extended_annotation.gtf` | Annotation GTF written by LRAA, or by Bambu-pipe when novel isoforms are discovered from ONT data. |
| `path/to/flames.sif` | FLAMESv2 Singularity image. |
| `path/to/repeatmasker.out` | RepeatMasker `.out` annotation table of `path/to/genome.fa`, copied from `genome.fa.out`. |
| `path/to/TE_annotation.gtf` | TE annotation GTF produced by miniTEQuant from `path/to/repeatmasker.out`. |
| `path/to/filtered_feature_bc_matrix` | Transcript-by-cell count matrix in 10x Market Exchange format (`barcodes.tsv`, `features.tsv`, `matrix.mtx`), derived from the FLAMESv2 Oarfish output. |

The annotation supplied to FLAMESv2 is also the annotation supplied to miniTEQuant. Without novel-isoform discovery that file is `path/to/genes.gtf`. With novel-isoform discovery it is `path/to/extended_annotation.gtf`.

## Usage of Recommended Tools

The workflow is organized into five major steps. Each step can be run independently or integrated into a workflow management system such as Snakemake or Nextflow. A file that is reused in a later step keeps the same path throughout this document.

Set `THREADS` to the number of available cores. Activate the environment named in each command before running it.

### Data Quality Control and Filtering

Quality control uses fastplong 0.4.1 on `path/to/reads.fastq.gz`. Both platforms use the thresholds applied in the benchmark: discard reads with mean Phred quality below 20 (`-m 20`) or length below 100 bp (`-l 100`), and disable adapter trimming (`-A`). HTML and JSON reports are written beside the filtered FASTQ.

#### PacBio

```bash
conda activate fastplong
fastplong \
    -i path/to/reads.fastq.gz \
    -o path/to/reads_filtered.fastq.gz \
    -h path/to/reads_filtered_report.html \
    -j path/to/reads_filtered_report.json \
    -m 20 \
    -l 100 \
    -w "$THREADS" \
    -A
```

#### ONT

```bash
conda activate fastplong
fastplong \
    -i path/to/reads.fastq.gz \
    -o path/to/reads_filtered.fastq.gz \
    -h path/to/reads_filtered_report.html \
    -j path/to/reads_filtered_report.json \
    -m 20 \
    -l 100 \
    -w "$THREADS" \
    -A
```

`path/to/reads_filtered.fastq.gz` is the read file used by wf-single-cell and FLAMESv2. ONT isoform discovery with Bambu-pipe reads the tagged BAM produced from this file, not the FASTQ itself.

### Processing Cell Barcodes and UMIs

This step produces a coordinate-sorted BAM in which the corrected cell barcode is stored in the `CB` tag and the corrected UMI in the `UB` tag.

If the input is already such a BAM, skip this step and use that file as `path/to/tagged.bam`.

#### ONT FASTQ

Run wf-single-cell v3.3.4 on `path/to/reads_filtered.fastq.gz`. `--kit` follows the 10x library; `3prime:v3` is the value for Chromium 3' v3 and Next GEM 3' v3.1. `--expected_cells` is the expected number of cells. The reference directory is `path/to/ref_genome_dir`.

```bash
export NXF_VER=26.04.4
export NXF_SYNTAX_PARSER=v1
export NXF_OFFLINE=true
nextflow run epi2me-labs/wf-single-cell -r v3.3.4 \
    -profile singularity \
    --fastq path/to/reads_filtered.fastq.gz \
    --expected_cells EXPECTED_CELLS \
    --kit '3prime:v3' \
    --ref_genome_dir path/to/ref_genome_dir \
    --out_dir path/to/wf_output \
    --threads "$THREADS" \
    -resume
```

The alignment consumed by later steps is the per-sample file written under `path/to/wf_output`. Copy or link it to `path/to/tagged.bam`, and confirm that `path/to/tagged.bam.bai` exists:

```bash
conda activate lraa
samtools index path/to/tagged.bam
```

#### PacBio

FLAMESv2 assigns barcodes and UMIs with flexiplex and aligns the retained reads to `path/to/genome.fa`. The whitelist is `path/to/barcodes.txt`. Isoform discovery inside FLAMESv2 is turned off; novel isoforms, when required, are discovered with LRAA. Quantification uses Oarfish.

Bind the parent directory that contains the FASTQ, reference, whitelist, and image, then run:

```bash
export THREADS
singularity exec -e \
    --bind path/to:path/to \
    path/to/flames.sif \
    Rscript path/to/run_flames.R
```

`path/to/run_flames.R`:

```r
options(bspm.sudo = TRUE)
basilisk::setBasiliskFork(FALSE)
suppressPackageStartupMessages(library(FLAMES))

outdir   <- "path/to/flames_output"
fastq    <- "path/to/reads_filtered.fastq.gz"
annot    <- "path/to/genes.gtf"
genome   <- "path/to/genome.fa"
barcodes <- "path/to/barcodes.txt"
threads  <- as.integer(Sys.getenv("THREADS", "8"))

dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
cfg <- create_config(
  outdir,
  pipeline_parameters.demultiplexer = "flexiplex",
  do_isoform_identification = FALSE,
  bambu_isoform_identification = FALSE,
  oarfish_quantification = TRUE,
  threads = threads
)

pipeline <- SingleCellPipeline(
  config_file   = cfg,
  outdir        = outdir,
  fastq         = c(fastq),
  annotation    = annot,
  genome_fa     = genome,
  barcodes_file = barcodes
)
pipeline <- run_FLAMES(pipeline)
saveRDS(pipeline, file.path(outdir, "pipeline.rds"))
```

The tagged genome alignment from this run is `path/to/flames_output/align2genome.bam`. Use it downstream as `path/to/align2genome.bam`. When novel-isoform discovery is not required, this same run is the quantification step: its annotation is `path/to/genes.gtf`, and the Oarfish matrix in `path/to/flames_output` is the matrix converted in [Transcript Identification and Quantification](#transcript-identification-and-quantification).

### Transcript Identification and Quantification

First decide whether transcript models beyond `path/to/genes.gtf` are required.

#### Novel-isoform discovery

On ONT, discover isoforms with LRAA 0.15.0 or Bambu-pipe 0.9.1. On PacBio, discover isoforms with LRAA 0.15.0. Either result is subsequently referred to as `path/to/extended_annotation.gtf`, and that file replaces `path/to/genes.gtf` as the annotation for FLAMESv2 quantification.

**LRAA.** Sort the BAM by coordinate when its header does not already report `SO:coordinate`, then index it. Mitochondrial contigs listed in `--oversimplify` follow the chromosome names in `path/to/genome.fa`; `chrM` matches the GRCh38 contig name. LRAA writes `path/to/extended_annotation.gtf`.

For ONT, and for a BAM that already carries `CB` and `UB`, the input alignment is `path/to/tagged.bam`:

```bash
conda activate lraa
samtools index path/to/tagged.bam

LRAA \
    --genome path/to/genome.fa \
    --bam path/to/tagged.bam \
    --gtf path/to/genes.gtf \
    --output_prefix path/to/extended_annotation \
    --cell_barcode_tag CB \
    --read_umi_tag UB \
    --num_parallel_contigs 4 \
    --num_threads_per_worker "$THREADS" \
    --oversimplify chrM
```

For PacBio HiFi, the input alignment is `path/to/align2genome.bam` and `--HiFi` is set:

```bash
conda activate lraa
samtools index path/to/align2genome.bam

LRAA \
    --genome path/to/genome.fa \
    --bam path/to/align2genome.bam \
    --gtf path/to/genes.gtf \
    --output_prefix path/to/extended_annotation \
    --cell_barcode_tag CB \
    --read_umi_tag UB \
    --num_parallel_contigs 4 \
    --num_threads_per_worker "$THREADS" \
    --oversimplify chrM \
    --HiFi
```

**Bambu-pipe.** Bambu-pipe is the ONT discovery route. PacBio discovery uses LRAA. The sample sheet `path/to/samplesheet.csv` points at `path/to/tagged.bam`, the coordinate-sorted BAM written by wf-single-cell. [Bambu-pipe](https://github.com/GoekeLab/bambu-pipe) accepts that BAM in the `path` column and then skips its own preprocessing and alignment. The same documentation requires the cell barcode and UMI to be stored in the `CB` and `UB` tags, or encoded in the read name as `<cell_barcode>_<UMI>#<read_id>`. The BAM from wf-single-cell uses `CB` and `UB`, and `samtools index` writes `path/to/tagged.bam.bai` beside it. The `sample` field must be the BAM filename without `.bam`, so the pipeline reads `<sample>.bam` and finds `<sample>.bam.bai` under that same name. For `path/to/tagged.bam` the sample name is `tagged`. Set `technology` to `ONT` and `chemistry` to the library chemistry (`10x3v3` for 10x Chromium 3' v3). `--quantification_mode no_quant` retains transcript discovery and writes the extended annotation; cell-level counts are produced by FLAMESv2.

```csv
sample,path,chemistry,technology
tagged,path/to/tagged.bam,10x3v3,ONT
```

```bash
cd path/to/bambu-pipe
nextflow -c path/to/lowmem.config run main.nf \
    --input path/to/samplesheet.csv \
    --genome path/to/genome.fa \
    --annotation path/to/genes.gtf \
    --output_dir path/to/bambu_output \
    --chemistry 10x3v3 \
    --technology ONT \
    --qscore_filtering false \
    --quantification_mode no_quant \
    -profile singularity,local
```

`MINIMAP_BUILD_INDEX` runs `minimap2 -k15 -w5 -d ref.mmi` on the whole genome. On a 16 GB host that build reached about 15 GB and was killed by the OOM killer. Alignment then pipes into `samtools sort -@ 8`, and the two processes together reached about 15 GB again. With `-I 500M` and `-k15 -w5`, one genome chunk still used about 8 GB, and a larger chunk exhausted a 16 GB host. `path/to/lowmem.config` caps each task at 2 CPUs and binds wrappers over minimap2 and samtools in the alignment image. The minimap2 wrapper does not dump the full index; alignment keeps `-k15 -w5` and adds `-I 200M --split-prefix`. The samtools wrapper adds `-m 200M` to `sort`. Hosts with at least 32 GB can omit `-c path/to/lowmem.config`.

`path/to/lowmem.config`:

```groovy
process {
    resourceLimits = [
        cpus: 2,
        memory: 12.GB
    ]
}
singularity {
    runOptions = "--bind ${env('PWD')} --bind path/to/minimap2.bambu.real:/opt/minimap2.real --bind path/to/mm2bambu.sh:/opt/conda/bin/minimap2 --bind path/to/samtools.bambu.real:/opt/conda/bin/samtools.real --bind path/to/samtools.bambu.sh:/opt/conda/bin/samtools --bind path/to/genome.fa.dir:/genome"
}
```

Copy both image binaries once. `path/to/genome.fa.dir` is the directory that contains `genome.fa`. Bind `samtools` back under `/opt/conda/bin/`; the conda build looks for `libhts.so.3` next to that directory, and a path outside it fails to start. `path/to/mm2bambu.sh` keeps `/genome/genome.fa` as the reference and the FASTQ as the query. `path/to/samtools.bambu.sh` runs `sort` with `-m 200M` and forwards every other samtools command unchanged.

```bash
singularity exec -e path/to/minimap2_samtools.img \
    cp /opt/conda/bin/minimap2 path/to/minimap2.bambu.real
singularity exec -e path/to/minimap2_samtools.img \
    cp /opt/conda/bin/samtools path/to/samtools.bambu.real
```

```bash
#!/bin/bash
export LD_LIBRARY_PATH="/opt/conda/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
real=/opt/conda/bin/samtools.real
if [[ "${1:-}" == "sort" ]]; then
  shift
  exec "$real" sort -m 200M "$@"
fi
exec "$real" "$@"
```

```bash
#!/bin/bash
real=/opt/minimap2.real
if [[ "${1:-}" == "--version" || "${1:-}" == "-V" || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  exec "$real" "$@"
fi
dump=""
opts=()
pos=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d) dump="$2"; shift 2 ;;
    *.mmi) shift ;;
    -ax|--junc-bed|-t|-k|-w|-I|--split-prefix)
      opts+=("$1" "$2"); shift 2 ;;
    -*) opts+=("$1"); shift ;;
    *) pos+=("$1"); shift ;;
  esac
done
if [[ -n "$dump" ]]; then
  printf 'placeholder\n' > "$dump"
  exit 0
fi
prefix="${MM2_SPLIT_PREFIX:-/tmp/mm2bambu}"
mkdir -p "$(dirname "$prefix")"
exec "$real" -I 200M --split-prefix "$prefix" -k15 -w5 "${opts[@]}" /genome/genome.fa "${pos[@]}"
```

On the test library, Bambu 3.11.1 in the v0.9.1 container finishes transcript discovery. When `--ndr` is omitted, Bambu recommends an NDR of 0 and `extended_annotations.gtf` contains the reference transcripts. `--ndr 0.1` is accepted; that test BAM still adds no row with `novelTranscript "TRUE"`.

Copy `path/to/bambu_output/extended_annotations.gtf` to `path/to/extended_annotation.gtf`.

#### Quantification with FLAMESv2

FLAMESv2 quantifies `path/to/reads_filtered.fastq.gz` against `path/to/barcodes.txt` and `path/to/genome.fa`. A pre-existing tagged BAM is the input to LRAA; the quantification command still reads the filtered FASTQ. Use the R script in the PacBio barcode section and set `annot` as follows.

- When novel-isoform discovery was not performed, `annot` is `path/to/genes.gtf`. On PacBio, the FLAMESv2 run that assigned barcodes has already completed this quantification.
- When novel-isoform discovery was performed, `annot` is `path/to/extended_annotation.gtf`. Run FLAMESv2 again with that annotation. The read file remains `path/to/reads_filtered.fastq.gz`, the whitelist remains `path/to/barcodes.txt`, and the genome remains `path/to/genome.fa`.

Oarfish writes three files into `path/to/flames_output`: `oarfish.count.mtx`, `oarfish.features.txt`, and `oarfish.barcodes.txt`. Copy them into a directory and rename them to the 10x Market Exchange filenames. Oarfish stores cells as rows and transcripts as columns. miniTEQuant reads transcripts as rows and cells as columns. `fix_matrix_transpose.py`, in this repository, transposes `matrix.mtx` and copies `barcodes.tsv` and `features.tsv` unchanged. The script imports SciPy, which is provided by the `miniTEQuant` environment.

```bash
mkdir -p path/to/oarfish_mex
cp path/to/flames_output/oarfish.barcodes.txt path/to/oarfish_mex/barcodes.tsv
cp path/to/flames_output/oarfish.features.txt path/to/oarfish_mex/features.tsv
cp path/to/flames_output/oarfish.count.mtx path/to/oarfish_mex/matrix.mtx
conda activate miniTEQuant
python path/to/fix_matrix_transpose.py path/to/oarfish_mex path/to/filtered_feature_bc_matrix
```

`path/to/filtered_feature_bc_matrix` is the transposed quantification matrix used for TE quantification and transcript classification. Transcript identifiers in `features.tsv` are the identifiers assigned under the annotation supplied to FLAMESv2.

### TE Locus and Subfamily-Level Quantification

Screen `path/to/genome.fa` once with RepeatMasker. `-species` is the organism of that genome. The reference used with the `chrM` contig name is human, so the value is `human`. RepeatMasker writes `genome.fa.out` under `path/to/repeatmasker_output`. Copy that annotation table to `path/to/repeatmasker.out`.

```bash
conda activate repeatmasker
mkdir -p path/to/repeatmasker_output
RepeatMasker \
    -species human \
    -engine rmblast \
    -pa "$THREADS" \
    -dir path/to/repeatmasker_output \
    path/to/genome.fa
cp path/to/repeatmasker_output/genome.fa.out path/to/repeatmasker.out
```

`path/to/repeatmasker.out` is the `.out` table read by `create_simple_TE_gtf.py`. Sequence names in the table are the names in `path/to/genome.fa`. Build the TE annotation from this file, then quantify TE loci and subfamilies with `cal_TE`. The transcript GTF must be the annotation used for the count matrix: `path/to/genes.gtf`, or `path/to/extended_annotation.gtf` after novel-isoform discovery.

```bash
conda activate miniTEQuant
cd path/to/miniTEQuant

python isoform_quantification/TE_analyse/create_simple_TE_gtf.py \
    -i path/to/repeatmasker.out \
    -o path/to/TE_annotation.gtf

python isoform_quantification/main.py cal_TE \
    -gtf path/to/genes.gtf \
    -te_gtf path/to/TE_annotation.gtf \
    --custom_sc_quant path/to/filtered_feature_bc_matrix \
    -t "$THREADS" \
    -o path/to/te_quant
```

When the count matrix was generated with `path/to/extended_annotation.gtf`, pass that same file to `-gtf` in place of `path/to/genes.gtf`.

`cal_TE` writes `path/to/te_quant/transcript_quantification_with_TE.tsv` for every transcript in the GTF. The `transcript_id` column is the transcript identifier, and `transcript_classification` is `Gene-alone`, `TE-alone`, or `TE-Gene`. Per-cell results are written to `path/to/te_quant/Custom_SC_TE_output`:

| File | Content |
| --- | --- |
| `cell_transcript_classification_counts.tsv` | Per-cell transcript records. Column 1 is the transcript identifier from the GTF, and column 11 is its class. |
| `cell_te_class_counts.tsv` | Counts aggregated to TE class. |
| `cell_te_family_counts.tsv` | Counts aggregated to TE family. |
| `cell_te_subfamily_counts_barcodes.tsv` | Cell barcodes for the subfamily matrix. |
| `cell_te_subfamily_counts_features.tsv` | TE subfamily identifiers. |
| `cell_te_subfamily_counts_matrix.mtx` | Cell-by-subfamily count matrix. |
| `cell_te_loci_counts_barcodes.tsv` | Cell barcodes for the locus matrix. |
| `cell_te_loci_counts_features.tsv` | TE locus identifiers. |
| `cell_te_loci_counts_matrix.mtx` | Cell-by-locus count matrix. |

The subfamily and locus matrices follow the Market Exchange convention, with features as rows and cells as columns. They are read by `Seurat::ReadMtx()` or `scanpy.read_mtx()`.

### Transcript Classification

After the 10x matrix and `path/to/te_quant/transcript_quantification_with_TE.tsv` have been written, `split_by_transcript_classification.py` splits the matrix into Gene-alone, TE-alone, and TE–Gene. The first field of each `features.tsv` row is matched to `transcript_id`. A transcript that does not carry one of those three labels is written to `others`. Plain text and gzip-compressed inputs are both accepted. The command below is run from the matrix directory and uses the gzip-compressed files.

```bash
cd path/to/filtered_feature_bc_matrix
python path/to/split_by_transcript_classification.py \
    --barcodes ./barcodes.tsv.gz \
    --features ./features.tsv.gz \
    --matrix ./matrix.mtx.gz \
    --quant path/to/te_quant/transcript_quantification_with_TE.tsv
```

The script writes `Gene-alone/`, `TE-alone/`, `TE-Gene/`, and `others/` in the directory that contains `matrix.mtx.gz`. Each directory contains the barcode file and the feature and count rows for that class. The same arguments accept the uncompressed `barcodes.tsv`, `features.tsv`, and `matrix.mtx` produced by the Oarfish rename step.

## Full Pipeline Examples

Run each block from the repository root. Reads, the reference, the barcode whitelist, and the TE annotation come from `test/`. Each route writes its own results under `results/`. `flames.sif` is the FLAMESv2 image from [Installation](#installation-of-recommended-tools). Place the miniTEQuant clone at `miniTEQuant/` relative to that root, or substitute its path in the `python` commands. `bambu-pipe/` is Bambu-pipe 0.9.1. `fix_matrix_transpose.py` is the transpose script in this repository. Comments name the step.

The test FASTQ is smaller than the wf-single-cell default cell filters (`min_features` 200, `min_cells` 3, `max_mito` 20). Those defaults remove every cell and stop in `process_matrix`. The ONT examples below set `--matrix_min_genes 1`, `--matrix_min_cells 1`, and `--matrix_max_mito 100`.

| File | Role |
| --- | --- |
| `test/01-test-data/ONT/test.fastq` | ONT test reads |
| `test/01-test-data/PacBio/test.fastq` | PacBio test reads |
| `test/02-reference/fasta/genome.fa` | Reference genome |
| `test/02-reference/genes/genes.gtf` | Reference gene annotation |
| `test/02-reference` | 10x reference directory for wf-single-cell |
| `test/01-test-data/barcodes/3M-february-2018.txt` | Cell-barcode whitelist |
| `test/02-reference/TE-annotation/hg38_filtered_chromosomes.gtf` | TE annotation used by `cal_TE` |

`genome.fa`, `genes.gtf`, and `hg38_filtered_chromosomes.gtf` are not stored in this repository. Download them, together with `wf-single-cell.sif`, `wf-common.sif`, and `flames.sif`, from the record in [Test data and images](#test-data-and-images).

| Route | Barcode and UMI | Discovery | Annotation passed to FLAMESv2 and `cal_TE` |
| --- | --- | --- | --- |
| ONT, reference annotation | wf-single-cell | — | `test/02-reference/genes/genes.gtf` |
| ONT, LRAA | wf-single-cell | LRAA | `results/ONT/LRAA/extended_annotation.gtf` |
| ONT, Bambu-pipe | wf-single-cell | Bambu-pipe | `results/ONT/Bambu-pipe/extended_annotation.gtf` |
| PacBio, reference annotation | FLAMESv2 | — | `test/02-reference/genes/genes.gtf` |
| PacBio, LRAA | FLAMESv2 | LRAA | `results/PacBio/LRAA/extended_annotation.gtf` |

On a discovery route, FLAMESv2 is run again after the extended annotation exists. On PacBio the first FLAMESv2 run assigns barcodes and, for LRAA, supplies the genome alignment.

### ONT, reference annotation

```bash
# Run these commands from the repository root
THREADS=8
export PATH="$HOME/.local/bin:$PATH"

# Discard reads with mean quality below 20 or length below 100 bp
conda activate fastplong
mkdir -p results/ONT/reference
fastplong \
    -i test/01-test-data/ONT/test.fastq \
    -o results/ONT/reference/test_filtered.fastq.gz \
    -h results/ONT/reference/test_filtered_report.html \
    -j results/ONT/reference/test_filtered_report.json \
    -m 20 \
    -l 100 \
    -w "$THREADS" \
    -A

conda deactivate
# Assign ONT cell barcodes and UMIs, then align reads
export NXF_VER=26.04.4
export NXF_SYNTAX_PARSER=v1
export NXF_OFFLINE=true
mkdir -p results/ONT/reference/wf_output results/ONT/reference/wf_work
nextflow run epi2me-labs/wf-single-cell -r v3.3.4 \
    -profile singularity,local \
    --fastq results/ONT/reference/test_filtered.fastq.gz \
    --sample test \
    --expected_cells 2000 \
    --kit '3prime:v3' \
    --ref_genome_dir test/02-reference \
    --out_dir results/ONT/reference/wf_output \
    --threads "$THREADS" \
    --matrix_min_genes 1 \
    --matrix_min_cells 1 \
    --matrix_max_mito 100 \
    -work-dir results/ONT/reference/wf_work \
    -resume

# Coordinate-sort and index the tagged BAM
conda activate lraa
samtools sort -@ "$THREADS" \
    -o results/ONT/reference/tagged.bam \
    results/ONT/reference/wf_output/test/test.tagged.bam
samtools index results/ONT/reference/tagged.bam

# Quantify transcripts with FLAMESv2
mkdir -p results/ONT/reference/flames_output
cat > results/ONT/reference/flames_output/run_flames.R <<'EOF'
options(bspm.sudo = TRUE)
basilisk::setBasiliskFork(FALSE)
suppressPackageStartupMessages(library(FLAMES))
outdir   <- "results/ONT/reference/flames_output"
fastq    <- "results/ONT/reference/test_filtered.fastq.gz"
annot    <- "test/02-reference/genes/genes.gtf"
genome   <- "test/02-reference/fasta/genome.fa"
barcodes <- "test/01-test-data/barcodes/3M-february-2018.txt"
threads  <- 8L
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
cfg <- create_config(
  outdir,
  pipeline_parameters.demultiplexer = "flexiplex",
  do_isoform_identification = FALSE,
  bambu_isoform_identification = FALSE,
  oarfish_quantification = TRUE,
  threads = threads
)
pipeline <- SingleCellPipeline(
  config_file = cfg, outdir = outdir, fastq = c(fastq),
  annotation = annot, genome_fa = genome, barcodes_file = barcodes
)
pipeline <- run_FLAMES(pipeline)
saveRDS(pipeline, file.path(outdir, "pipeline.rds"))
EOF
singularity exec -e --bind "$PWD:$PWD" flames.sif Rscript results/ONT/reference/flames_output/run_flames.R

# Rename the Oarfish files, transpose the matrix, and gzip the 10x files
mkdir -p results/ONT/reference/oarfish_mex
cp results/ONT/reference/flames_output/oarfish.barcodes.txt results/ONT/reference/oarfish_mex/barcodes.tsv
cp results/ONT/reference/flames_output/oarfish.features.txt results/ONT/reference/oarfish_mex/features.tsv
cp results/ONT/reference/flames_output/oarfish.count.mtx results/ONT/reference/oarfish_mex/matrix.mtx
conda activate miniTEQuant
python fix_matrix_transpose.py \
    results/ONT/reference/oarfish_mex \
    results/ONT/reference/filtered_feature_bc_matrix
gzip -c results/ONT/reference/filtered_feature_bc_matrix/barcodes.tsv > results/ONT/reference/filtered_feature_bc_matrix/barcodes.tsv.gz
gzip -c results/ONT/reference/filtered_feature_bc_matrix/features.tsv > results/ONT/reference/filtered_feature_bc_matrix/features.tsv.gz
gzip -c results/ONT/reference/filtered_feature_bc_matrix/matrix.mtx > results/ONT/reference/filtered_feature_bc_matrix/matrix.mtx.gz

# Quantify TE loci and subfamilies
conda activate miniTEQuant
python miniTEQuant/isoform_quantification/main.py cal_TE \
    -gtf test/02-reference/genes/genes.gtf \
    -te_gtf test/02-reference/TE-annotation/hg38_filtered_chromosomes.gtf \
    --custom_sc_quant results/ONT/reference/filtered_feature_bc_matrix \
    -t "$THREADS" \
    -o results/ONT/reference/te_quant

# Split transcripts into Gene-alone, TE-alone, and TE-Gene
python split_by_transcript_classification.py \
    --barcodes results/ONT/reference/filtered_feature_bc_matrix/barcodes.tsv.gz \
    --features results/ONT/reference/filtered_feature_bc_matrix/features.tsv.gz \
    --matrix results/ONT/reference/filtered_feature_bc_matrix/matrix.mtx.gz \
    --quant results/ONT/reference/te_quant/transcript_quantification_with_TE.tsv
```

### ONT, LRAA discovery

LRAA reads `results/ONT/LRAA/tagged.bam` and writes `results/ONT/LRAA/extended_annotation.gtf`.

```bash
# Run these commands from the repository root
THREADS=8
export PATH="$HOME/.local/bin:$PATH"

# Discard reads with mean quality below 20 or length below 100 bp
conda activate fastplong
mkdir -p results/ONT/LRAA
fastplong \
    -i test/01-test-data/ONT/test.fastq \
    -o results/ONT/LRAA/test_filtered.fastq.gz \
    -h results/ONT/LRAA/test_filtered_report.html \
    -j results/ONT/LRAA/test_filtered_report.json \
    -m 20 \
    -l 100 \
    -w "$THREADS" \
    -A

conda deactivate

# Assign ONT cell barcodes and UMIs, then align reads
export NXF_VER=26.04.4
export NXF_SYNTAX_PARSER=v1
export NXF_OFFLINE=true
mkdir -p results/ONT/LRAA/wf_output results/ONT/LRAA/wf_work
nextflow run epi2me-labs/wf-single-cell -r v3.3.4 \
    -profile singularity \
    --fastq results/ONT/LRAA/test_filtered.fastq.gz \
    --sample test \
    --expected_cells 2000 \
    --kit '3prime:v3' \
    --ref_genome_dir test/02-reference \
    --out_dir results/ONT/LRAA/wf_output \
    --threads "$THREADS" \
    --matrix_min_genes 1 \
    --matrix_min_cells 1 \
    --matrix_max_mito 100 \
    -work-dir results/ONT/LRAA/wf_work \
    -resume

# Coordinate-sort and index the tagged BAM
conda activate lraa
samtools sort -@ "$THREADS" \
    -o results/ONT/LRAA/tagged.bam \
    results/ONT/LRAA/wf_output/test/test.tagged.bam
samtools index results/ONT/LRAA/tagged.bam

# Discover isoforms with LRAA
LRAA \
    --genome test/02-reference/fasta/genome.fa \
    --bam results/ONT/LRAA/tagged.bam \
    --gtf test/02-reference/genes/genes.gtf \
    --output_prefix results/ONT/LRAA/extended_annotation \
    --cell_barcode_tag CB \
    --read_umi_tag UB \
    --num_parallel_contigs 4 \
    --num_threads_per_worker "$THREADS" \
    --oversimplify chrM

# Quantify transcripts with FLAMESv2
mkdir -p results/ONT/LRAA/flames_output
cat > results/ONT/LRAA/flames_output/run_flames.R <<'EOF'
options(bspm.sudo = TRUE)
basilisk::setBasiliskFork(FALSE)
suppressPackageStartupMessages(library(FLAMES))
outdir   <- "results/ONT/LRAA/flames_output"
fastq    <- "results/ONT/LRAA/test_filtered.fastq.gz"
annot    <- "results/ONT/LRAA/extended_annotation.gtf"
genome   <- "test/02-reference/fasta/genome.fa"
barcodes <- "test/01-test-data/barcodes/3M-february-2018.txt"
threads  <- 8L
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
cfg <- create_config(
  outdir,
  pipeline_parameters.demultiplexer = "flexiplex",
  do_isoform_identification = FALSE,
  bambu_isoform_identification = FALSE,
  oarfish_quantification = TRUE,
  threads = threads
)
pipeline <- SingleCellPipeline(
  config_file = cfg, outdir = outdir, fastq = c(fastq),
  annotation = annot, genome_fa = genome, barcodes_file = barcodes
)
pipeline <- run_FLAMES(pipeline)
saveRDS(pipeline, file.path(outdir, "pipeline.rds"))
EOF
singularity exec -e --bind "$PWD:$PWD" flames.sif Rscript results/ONT/LRAA/flames_output/run_flames.R

# Rename the Oarfish files, transpose the matrix, and gzip the 10x files
mkdir -p results/ONT/LRAA/oarfish_mex
cp results/ONT/LRAA/flames_output/oarfish.barcodes.txt results/ONT/LRAA/oarfish_mex/barcodes.tsv
cp results/ONT/LRAA/flames_output/oarfish.features.txt results/ONT/LRAA/oarfish_mex/features.tsv
cp results/ONT/LRAA/flames_output/oarfish.count.mtx results/ONT/LRAA/oarfish_mex/matrix.mtx
conda activate miniTEQuant
python fix_matrix_transpose.py \
    results/ONT/LRAA/oarfish_mex \
    results/ONT/LRAA/filtered_feature_bc_matrix
gzip -c results/ONT/LRAA/filtered_feature_bc_matrix/barcodes.tsv > results/ONT/LRAA/filtered_feature_bc_matrix/barcodes.tsv.gz
gzip -c results/ONT/LRAA/filtered_feature_bc_matrix/features.tsv > results/ONT/LRAA/filtered_feature_bc_matrix/features.tsv.gz
gzip -c results/ONT/LRAA/filtered_feature_bc_matrix/matrix.mtx > results/ONT/LRAA/filtered_feature_bc_matrix/matrix.mtx.gz

# Quantify TE loci and subfamilies
conda activate miniTEQuant
python miniTEQuant/isoform_quantification/main.py cal_TE \
    -gtf results/ONT/LRAA/extended_annotation.gtf \
    -te_gtf test/02-reference/TE-annotation/hg38_filtered_chromosomes.gtf \
    --custom_sc_quant results/ONT/LRAA/filtered_feature_bc_matrix \
    -t "$THREADS" \
    -o results/ONT/LRAA/te_quant

# Split transcripts into Gene-alone, TE-alone, and TE-Gene
python split_by_transcript_classification.py \
    --barcodes results/ONT/LRAA/filtered_feature_bc_matrix/barcodes.tsv.gz \
    --features results/ONT/LRAA/filtered_feature_bc_matrix/features.tsv.gz \
    --matrix results/ONT/LRAA/filtered_feature_bc_matrix/matrix.mtx.gz \
    --quant results/ONT/LRAA/te_quant/transcript_quantification_with_TE.tsv
```

### ONT, Bambu-pipe discovery

Bambu-pipe reads `results/ONT/Bambu-pipe/tagged.bam` and writes `results/ONT/Bambu-pipe/extended_annotation.gtf`.

```bash
# Run these commands from the repository root
THREADS=8
export PATH="$HOME/.local/bin:$PATH"

# Discard reads with mean quality below 20 or length below 100 bp
conda activate fastplong
mkdir -p results/ONT/Bambu-pipe
fastplong \
    -i test/01-test-data/ONT/test.fastq \
    -o results/ONT/Bambu-pipe/test_filtered.fastq.gz \
    -h results/ONT/Bambu-pipe/test_filtered_report.html \
    -j results/ONT/Bambu-pipe/test_filtered_report.json \
    -m 20 \
    -l 100 \
    -w "$THREADS" \
    -A

conda deactivate

# Assign ONT cell barcodes and UMIs, then align reads
export NXF_VER=26.04.4
export NXF_SYNTAX_PARSER=v1
export NXF_OFFLINE=true
mkdir -p results/ONT/Bambu-pipe/wf_output results/ONT/Bambu-pipe/wf_work
nextflow run epi2me-labs/wf-single-cell -r v3.3.4 \
    -profile singularity \
    --fastq results/ONT/Bambu-pipe/test_filtered.fastq.gz \
    --sample test \
    --expected_cells 2000 \
    --kit '3prime:v3' \
    --ref_genome_dir test/02-reference \
    --out_dir results/ONT/Bambu-pipe/wf_output \
    --threads "$THREADS" \
    --matrix_min_genes 1 \
    --matrix_min_cells 1 \
    --matrix_max_mito 100 \
    -work-dir results/ONT/Bambu-pipe/wf_work \
    -resume

# Coordinate-sort and index the tagged BAM
conda activate lraa
samtools sort -@ "$THREADS" \
    -o results/ONT/Bambu-pipe/tagged.bam \
    results/ONT/Bambu-pipe/wf_output/test/test.tagged.bam
samtools index results/ONT/Bambu-pipe/tagged.bam

# Discover isoforms with Bambu-pipe.
# test/01-test-data/samplesheet/ONT.csv sets sample to the BAM filename without .bam,
# so tagged.bam is read with tagged.bam.bai.
export NXF_VER=26.04.4
nextflow run bambu-pipe/main.nf \
    --input test/01-test-data/samplesheet/ONT.csv \
    --genome test/02-reference/fasta/genome.fa \
    --annotation test/02-reference/genes/genes.gtf \
    --output_dir results/ONT/Bambu-pipe/bambu_output \
    --chemistry 10x3v3 \
    --technology ONT \
    --qscore_filtering false \
    --quantification_mode no_quant \
    -profile singularity,local \
    -work-dir results/ONT/Bambu-pipe/bambu_work \
    -resume
cp results/ONT/Bambu-pipe/bambu_output/extended_annotations.gtf results/ONT/Bambu-pipe/extended_annotation.gtf

# Quantify transcripts with FLAMESv2
mkdir -p results/ONT/Bambu-pipe/flames_output
cat > results/ONT/Bambu-pipe/flames_output/run_flames.R <<'EOF'
options(bspm.sudo = TRUE)
basilisk::setBasiliskFork(FALSE)
suppressPackageStartupMessages(library(FLAMES))
outdir   <- "results/ONT/Bambu-pipe/flames_output"
fastq    <- "results/ONT/Bambu-pipe/test_filtered.fastq.gz"
annot    <- "results/ONT/Bambu-pipe/extended_annotation.gtf"
genome   <- "test/02-reference/fasta/genome.fa"
barcodes <- "test/01-test-data/barcodes/3M-february-2018.txt"
threads  <- 8L
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
cfg <- create_config(
  outdir,
  pipeline_parameters.demultiplexer = "flexiplex",
  do_isoform_identification = FALSE,
  bambu_isoform_identification = FALSE,
  oarfish_quantification = TRUE,
  threads = threads
)
pipeline <- SingleCellPipeline(
  config_file = cfg, outdir = outdir, fastq = c(fastq),
  annotation = annot, genome_fa = genome, barcodes_file = barcodes
)
pipeline <- run_FLAMES(pipeline)
saveRDS(pipeline, file.path(outdir, "pipeline.rds"))
EOF
singularity exec -e --bind "$PWD:$PWD" flames.sif Rscript results/ONT/Bambu-pipe/flames_output/run_flames.R

# Rename the Oarfish files, transpose the matrix, and gzip the 10x files
mkdir -p results/ONT/Bambu-pipe/oarfish_mex
cp results/ONT/Bambu-pipe/flames_output/oarfish.barcodes.txt results/ONT/Bambu-pipe/oarfish_mex/barcodes.tsv
cp results/ONT/Bambu-pipe/flames_output/oarfish.features.txt results/ONT/Bambu-pipe/oarfish_mex/features.tsv
cp results/ONT/Bambu-pipe/flames_output/oarfish.count.mtx results/ONT/Bambu-pipe/oarfish_mex/matrix.mtx
conda activate miniTEQuant
python fix_matrix_transpose.py \
    results/ONT/Bambu-pipe/oarfish_mex \
    results/ONT/Bambu-pipe/filtered_feature_bc_matrix
gzip -c results/ONT/Bambu-pipe/filtered_feature_bc_matrix/barcodes.tsv > results/ONT/Bambu-pipe/filtered_feature_bc_matrix/barcodes.tsv.gz
gzip -c results/ONT/Bambu-pipe/filtered_feature_bc_matrix/features.tsv > results/ONT/Bambu-pipe/filtered_feature_bc_matrix/features.tsv.gz
gzip -c results/ONT/Bambu-pipe/filtered_feature_bc_matrix/matrix.mtx > results/ONT/Bambu-pipe/filtered_feature_bc_matrix/matrix.mtx.gz

# Quantify TE loci and subfamilies
conda activate miniTEQuant
python miniTEQuant/isoform_quantification/main.py cal_TE \
    -gtf results/ONT/Bambu-pipe/extended_annotation.gtf \
    -te_gtf test/02-reference/TE-annotation/hg38_filtered_chromosomes.gtf \
    --custom_sc_quant results/ONT/Bambu-pipe/filtered_feature_bc_matrix \
    -t "$THREADS" \
    -o results/ONT/Bambu-pipe/te_quant

# Split transcripts into Gene-alone, TE-alone, and TE-Gene
python split_by_transcript_classification.py \
    --barcodes results/ONT/Bambu-pipe/filtered_feature_bc_matrix/barcodes.tsv.gz \
    --features results/ONT/Bambu-pipe/filtered_feature_bc_matrix/features.tsv.gz \
    --matrix results/ONT/Bambu-pipe/filtered_feature_bc_matrix/matrix.mtx.gz \
    --quant results/ONT/Bambu-pipe/te_quant/transcript_quantification_with_TE.tsv
```

### PacBio, reference annotation

FLAMESv2 assigns barcodes and quantifies `test/02-reference/genes/genes.gtf`. This run also writes `results/PacBio/reference/flames_output/align2genome.bam`.

```bash
# Run these commands from the repository root
THREADS=8
export PATH="$HOME/.local/bin:$PATH"

# Discard reads with mean quality below 20 or length below 100 bp
conda activate fastplong
mkdir -p results/PacBio/reference
fastplong \
    -i test/01-test-data/PacBio/test.fastq \
    -o results/PacBio/reference/test_filtered.fastq.gz \
    -h results/PacBio/reference/test_filtered_report.html \
    -j results/PacBio/reference/test_filtered_report.json \
    -m 20 \
    -l 100 \
    -w "$THREADS" \
    -A

conda deactivate

# Quantify transcripts with FLAMESv2
mkdir -p results/PacBio/reference/flames_output
cat > results/PacBio/reference/flames_output/run_flames.R <<'EOF'
options(bspm.sudo = TRUE)
basilisk::setBasiliskFork(FALSE)
suppressPackageStartupMessages(library(FLAMES))
outdir   <- "results/PacBio/reference/flames_output"
fastq    <- "results/PacBio/reference/test_filtered.fastq.gz"
annot    <- "test/02-reference/genes/genes.gtf"
genome   <- "test/02-reference/fasta/genome.fa"
barcodes <- "test/01-test-data/barcodes/3M-february-2018.txt"
threads  <- 8L
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
cfg <- create_config(
  outdir,
  pipeline_parameters.demultiplexer = "flexiplex",
  do_isoform_identification = FALSE,
  bambu_isoform_identification = FALSE,
  oarfish_quantification = TRUE,
  threads = threads
)
pipeline <- SingleCellPipeline(
  config_file = cfg, outdir = outdir, fastq = c(fastq),
  annotation = annot, genome_fa = genome, barcodes_file = barcodes
)
pipeline <- run_FLAMES(pipeline)
saveRDS(pipeline, file.path(outdir, "pipeline.rds"))
EOF
singularity exec -e --bind "$PWD:$PWD" flames.sif Rscript results/PacBio/reference/flames_output/run_flames.R

# Rename the Oarfish files, transpose the matrix, and gzip the 10x files
mkdir -p results/PacBio/reference/oarfish_mex
cp results/PacBio/reference/flames_output/oarfish.barcodes.txt results/PacBio/reference/oarfish_mex/barcodes.tsv
cp results/PacBio/reference/flames_output/oarfish.features.txt results/PacBio/reference/oarfish_mex/features.tsv
cp results/PacBio/reference/flames_output/oarfish.count.mtx results/PacBio/reference/oarfish_mex/matrix.mtx
conda activate miniTEQuant
python fix_matrix_transpose.py \
    results/PacBio/reference/oarfish_mex \
    results/PacBio/reference/filtered_feature_bc_matrix
gzip -c results/PacBio/reference/filtered_feature_bc_matrix/barcodes.tsv > results/PacBio/reference/filtered_feature_bc_matrix/barcodes.tsv.gz
gzip -c results/PacBio/reference/filtered_feature_bc_matrix/features.tsv > results/PacBio/reference/filtered_feature_bc_matrix/features.tsv.gz
gzip -c results/PacBio/reference/filtered_feature_bc_matrix/matrix.mtx > results/PacBio/reference/filtered_feature_bc_matrix/matrix.mtx.gz

# Quantify TE loci and subfamilies
conda activate miniTEQuant
python miniTEQuant/isoform_quantification/main.py cal_TE \
    -gtf test/02-reference/genes/genes.gtf \
    -te_gtf test/02-reference/TE-annotation/hg38_filtered_chromosomes.gtf \
    --custom_sc_quant results/PacBio/reference/filtered_feature_bc_matrix \
    -t "$THREADS" \
    -o results/PacBio/reference/te_quant

# Split transcripts into Gene-alone, TE-alone, and TE-Gene
python split_by_transcript_classification.py \
    --barcodes results/PacBio/reference/filtered_feature_bc_matrix/barcodes.tsv.gz \
    --features results/PacBio/reference/filtered_feature_bc_matrix/features.tsv.gz \
    --matrix results/PacBio/reference/filtered_feature_bc_matrix/matrix.mtx.gz \
    --quant results/PacBio/reference/te_quant/transcript_quantification_with_TE.tsv
```

### PacBio, LRAA discovery

The first FLAMESv2 run writes the genome alignment. LRAA is called with `--HiFi` and the second FLAMESv2 run quantifies `results/PacBio/LRAA/extended_annotation.gtf`.

```bash
# Run these commands from the repository root
THREADS=8
export PATH="$HOME/.local/bin:$PATH"

# Discard reads with mean quality below 20 or length below 100 bp
conda activate fastplong
mkdir -p results/PacBio/LRAA
fastplong \
    -i test/01-test-data/PacBio/test.fastq \
    -o results/PacBio/LRAA/test_filtered.fastq.gz \
    -h results/PacBio/LRAA/test_filtered_report.html \
    -j results/PacBio/LRAA/test_filtered_report.json \
    -m 20 \
    -l 100 \
    -w "$THREADS" \
    -A

# Quantify transcripts with FLAMESv2
mkdir -p results/PacBio/LRAA/flames_align
cat > results/PacBio/LRAA/flames_align/run_flames.R <<'EOF'
options(bspm.sudo = TRUE)
basilisk::setBasiliskFork(FALSE)
suppressPackageStartupMessages(library(FLAMES))
outdir   <- "results/PacBio/LRAA/flames_align"
fastq    <- "results/PacBio/LRAA/test_filtered.fastq.gz"
annot    <- "test/02-reference/genes/genes.gtf"
genome   <- "test/02-reference/fasta/genome.fa"
barcodes <- "test/01-test-data/barcodes/3M-february-2018.txt"
threads  <- 8L
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
cfg <- create_config(
  outdir,
  pipeline_parameters.demultiplexer = "flexiplex",
  do_isoform_identification = FALSE,
  bambu_isoform_identification = FALSE,
  oarfish_quantification = TRUE,
  threads = threads
)
pipeline <- SingleCellPipeline(
  config_file = cfg, outdir = outdir, fastq = c(fastq),
  annotation = annot, genome_fa = genome, barcodes_file = barcodes
)
pipeline <- run_FLAMES(pipeline)
saveRDS(pipeline, file.path(outdir, "pipeline.rds"))
EOF
singularity exec -e --bind "$PWD:$PWD" flames.sif Rscript results/PacBio/LRAA/flames_align/run_flames.R

# Coordinate-sort and index the FLAMESv2 genome alignment
conda activate lraa
samtools sort -@ "$THREADS" -o results/PacBio/LRAA/align2genome.bam results/PacBio/LRAA/flames_align/align2genome.bam
samtools index results/PacBio/LRAA/align2genome.bam

# Discover isoforms with LRAA
LRAA \
    --genome test/02-reference/fasta/genome.fa \
    --bam results/PacBio/LRAA/align2genome.bam \
    --gtf test/02-reference/genes/genes.gtf \
    --output_prefix results/PacBio/LRAA/extended_annotation \
    --cell_barcode_tag CB \
    --read_umi_tag UB \
    --num_parallel_contigs 4 \
    --num_threads_per_worker "$THREADS" \
    --oversimplify chrM \
    --HiFi

# Quantify transcripts with FLAMESv2
mkdir -p results/PacBio/LRAA/flames_output
cat > results/PacBio/LRAA/flames_output/run_flames.R <<'EOF'
options(bspm.sudo = TRUE)
basilisk::setBasiliskFork(FALSE)
suppressPackageStartupMessages(library(FLAMES))
outdir   <- "results/PacBio/LRAA/flames_output"
fastq    <- "results/PacBio/LRAA/test_filtered.fastq.gz"
annot    <- "results/PacBio/LRAA/extended_annotation.gtf"
genome   <- "test/02-reference/fasta/genome.fa"
barcodes <- "test/01-test-data/barcodes/3M-february-2018.txt"
threads  <- 8L
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
cfg <- create_config(
  outdir,
  pipeline_parameters.demultiplexer = "flexiplex",
  do_isoform_identification = FALSE,
  bambu_isoform_identification = FALSE,
  oarfish_quantification = TRUE,
  threads = threads
)
pipeline <- SingleCellPipeline(
  config_file = cfg, outdir = outdir, fastq = c(fastq),
  annotation = annot, genome_fa = genome, barcodes_file = barcodes
)
pipeline <- run_FLAMES(pipeline)
saveRDS(pipeline, file.path(outdir, "pipeline.rds"))
EOF
singularity exec -e --bind "$PWD:$PWD" flames.sif Rscript results/PacBio/LRAA/flames_output/run_flames.R

# Rename the Oarfish files, transpose the matrix, and gzip the 10x files
mkdir -p results/PacBio/LRAA/oarfish_mex
cp results/PacBio/LRAA/flames_output/oarfish.barcodes.txt results/PacBio/LRAA/oarfish_mex/barcodes.tsv
cp results/PacBio/LRAA/flames_output/oarfish.features.txt results/PacBio/LRAA/oarfish_mex/features.tsv
cp results/PacBio/LRAA/flames_output/oarfish.count.mtx results/PacBio/LRAA/oarfish_mex/matrix.mtx
conda activate miniTEQuant
python fix_matrix_transpose.py \
    results/PacBio/LRAA/oarfish_mex \
    results/PacBio/LRAA/filtered_feature_bc_matrix
gzip -c results/PacBio/LRAA/filtered_feature_bc_matrix/barcodes.tsv > results/PacBio/LRAA/filtered_feature_bc_matrix/barcodes.tsv.gz
gzip -c results/PacBio/LRAA/filtered_feature_bc_matrix/features.tsv > results/PacBio/LRAA/filtered_feature_bc_matrix/features.tsv.gz
gzip -c results/PacBio/LRAA/filtered_feature_bc_matrix/matrix.mtx > results/PacBio/LRAA/filtered_feature_bc_matrix/matrix.mtx.gz

# Quantify TE loci and subfamilies
conda activate miniTEQuant
python miniTEQuant/isoform_quantification/main.py cal_TE \
    -gtf results/PacBio/LRAA/extended_annotation.gtf \
    -te_gtf test/02-reference/TE-annotation/hg38_filtered_chromosomes.gtf \
    --custom_sc_quant results/PacBio/LRAA/filtered_feature_bc_matrix \
    -t "$THREADS" \
    -o results/PacBio/LRAA/te_quant

# Split transcripts into Gene-alone, TE-alone, and TE-Gene
python split_by_transcript_classification.py \
    --barcodes results/PacBio/LRAA/filtered_feature_bc_matrix/barcodes.tsv.gz \
    --features results/PacBio/LRAA/filtered_feature_bc_matrix/features.tsv.gz \
    --matrix results/PacBio/LRAA/filtered_feature_bc_matrix/matrix.mtx.gz \
    --quant results/PacBio/LRAA/te_quant/transcript_quantification_with_TE.tsv
```

## Reproducibility

The recommended workflow is defined by the following versions and settings.

| Component | Version or image | Role |
| --- | --- | --- |
| fastplong | 0.4.1 | Quality control |
| Singularity image | `docker://ghcr.io/mritchielab/flames:20af1ce` | Barcode and UMI assignment, transcript quantification |
| wf-single-cell | 3.3.4 | ONT barcode and UMI assignment |
| LRAA | 0.15.0 | Reference-guided isoform discovery |
| Bambu-pipe | 0.9.1 | ONT reference-guided isoform discovery |
| Nextflow | 26.04.4 | Execution of wf-single-cell and Bambu-pipe |
| RepeatMasker | 4.2.4, Dfam 4.0 curated consensus | Annotation of `path/to/genome.fa` written to `path/to/repeatmasker.out` |
| miniTEQuant | `main` of [calm109/miniTEQuant](https://github.com/calm109/miniTEQuant) | TE annotation, locus and subfamily counts, transcript classes |

Record the commit of miniTEQuant used to create `path/to/TE_annotation.gtf` (`git -C path/to/miniTEQuant rev-parse HEAD`). Keep that GTF with the count matrix. FLAMESv2 quantification and `cal_TE -gtf` must receive the same annotation, either `path/to/genes.gtf` or `path/to/extended_annotation.gtf`.

Platform-specific settings that affect the matrices are the fastplong filters (`-m 20 -l 100 -A`), the wf-single-cell kit and expected cell number, the FLAMESv2 configuration (`flexiplex` demultiplexing, isoform identification disabled, Oarfish quantification enabled), the RepeatMasker settings (`-species human -engine rmblast`), and the LRAA tags `CB` and `UB`, with `--HiFi` restricted to PacBio. Cite each program from the publication linked in its repository when reporting results obtained with this workflow.

## Test data and images

`wf-single-cell.sif`, `wf-common.sif`, `flames.sif`, and the reference annotation placed under `test/02-reference` are distributed at <https://zenodo.org/records/24068965>. After downloading:

- Put `flames.sif` in the repository root. The examples call `singularity exec ... flames.sif`.
- Put `wf-single-cell.sif` and `wf-common.sif` at the absolute paths written into `.nextflow/assets/epi2me-labs/wf-single-cell/nextflow.config`.
- Put the reference files at `test/02-reference/fasta/genome.fa`, `test/02-reference/genes/genes.gtf`, and `test/02-reference/TE-annotation/hg38_filtered_chromosomes.gtf`.

## Memory

A host with at least 32 GB of RAM can run the commands in this document as written. The limits below were required on a host with about 16 GB of RAM and about 15 GB available to Nextflow. LRAA itself completed on that host, with a child-process peak of about 11 GB, and did not need a lower memory setting.

**wf-single-cell.** `build_minimap_index` requests 16 GB and runs `minimap2 -I 16G`. Nextflow refuses the task before it starts when the request exceeds available memory. Later processes request 31–32 GB and are refused for the same reason. In `.nextflow/assets/epi2me-labs/wf-single-cell/modules/local/common.nf`, set the `build_minimap_index` process to `memory '12 GB'` and change `-I 16G` to `-I 4G`. Save the following file as `host_limits.config` and add `-c host_limits.config` to `nextflow run`:

```groovy
process {
    resourceLimits = [
        cpus: 8,
        memory: 12.GB
    ]
}
```

`nextflow pull` can restore the original module. Reapply the `12 GB` and `-I 4G` edits after a pull. The ONT examples also need `-profile singularity,local` so the executor does not keep the higher default requests.

**FLAMESv2.** Genome alignment runs `minimap2` on `genome.fa`. On the 16 GB host that process reached about 15 GB and was killed by the OOM killer. A wrapper that only adds `-I 1G` splits the index and then emits a BAM without `@SQ` lines; FLAMESv2 stops with `Error in step genome_alignment: argument is missing, with no default`. The wrapper must also pass `--split-prefix`. Copy the image binary out once:

```bash
singularity exec -e flames.sif \
    cp /usr/local/lib/R/site-library/FLAMES/bin/minimap2 path/to/minimap2.flames.real
```

`path/to/mm2wrap.sh`:

```bash
#!/bin/bash
real=/opt/minimap2.flames.real
case "${1:-}" in
  --version|-V|--help|-h)
    exec "$real" "$@"
    ;;
esac
mkdir -p /tmp/mm2split
exec "$real" -I 1G --split-prefix /tmp/mm2split/part "$@"
```

Bind both files over the image and run the same R script:

```bash
singularity exec -e \
  --bind "$PWD:$PWD" \
  --bind "path/to/minimap2.flames.real:/opt/minimap2.flames.real" \
  --bind "path/to/mm2wrap.sh:/usr/local/lib/R/site-library/FLAMES/bin/minimap2" \
  flames.sif Rscript path/to/run_flames.R
```

**Bambu-pipe.** The documented ONT route reads a BAM, so it does not build the minimap2 index described in the FASTQ low-memory section above. With `-profile local`, read-class construction and transcript discovery are labeled `high_mem` and request 64 GB. Nextflow refuses those tasks on a 16 GB host before they start. Save `bambu_limits.config` and pass it with `-c bambu_limits.config`:

```groovy
process {
    resourceLimits = [
        cpus: 4,
        memory: 12.GB
    ]
    withLabel: 'low_mem'    { memory = 12.GB }
    withLabel: 'medium_mem' { memory = 12.GB }
    withLabel: 'high_mem'   { memory = 12.GB }
    withLabel: 'low_cpu'    { cpus = 2 }
    withLabel: 'medium_cpu' { cpus = 4 }
    withLabel: 'high_cpu'   { cpus = 4 }
}
```

With that cap, annotation preparation, read-class construction, and transcript discovery finished on the test BAM. Hosts with at least 64 GB can omit `-c bambu_limits.config`.

