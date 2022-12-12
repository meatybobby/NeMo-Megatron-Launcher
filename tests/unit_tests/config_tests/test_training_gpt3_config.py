from omegaconf import OmegaConf


class TestTrainingGPT3Config:
    def test_training_gpt3_config_126m(self):
        conf = OmegaConf.load("conf/training/gpt3/126m.yaml")
        s = """
        run:
          name: gpt3_126m
          results_dir: ${base_results_dir}/${.name}
          time_limit: "1-00:00:00"
          dependency: "singleton"
        
        trainer:
          num_nodes: 8
          devices: 8
          accelerator: gpu
          precision: bf16
          logger: False # logger provided by exp_manager
          enable_checkpointing: False
          replace_sampler_ddp: False
          max_epochs: null
          max_steps: 600000 # consumed_samples = global_step * global_batch_size
          max_time: "00:23:30:00" # days:hours:minutes:seconds
          log_every_n_steps: 10
          val_check_interval: 2000
          limit_val_batches: 50
          limit_test_batches: 50
          accumulate_grad_batches: 1
          gradient_clip_val: 1.0
        
        
        exp_manager:
          explicit_log_dir: ${training.run.results_dir}/results
          exp_dir: null
          name: megatron_gpt
          create_wandb_logger: False
          wandb_logger_kwargs:
            project: nemo_gpt3
            name: ${training.run.name}
          resume_if_exists: True
          resume_ignore_no_checkpoint: True
          create_checkpoint_callback: True
          checkpoint_callback_params:
            monitor: val_loss
            save_top_k: 10
            mode: min
            always_save_nemo: False # saves nemo file during validation, not implemented for model parallel
            save_nemo_on_train_end: False # not recommended when training large models on clusters with short time limits
            filename: 'megatron_gpt--{val_loss:.2f}-{step}-{consumed_samples}'
            model_parallel_size: ${multiply:${training.model.tensor_model_parallel_size}, ${training.model.pipeline_model_parallel_size}}
          log_step_timing: True
          step_timing_kwargs:
            sync_cuda: True
            buffer_size: 5
        
        model:
          micro_batch_size: 4
          global_batch_size: 256
          tensor_model_parallel_size: 1
          pipeline_model_parallel_size: 1
          virtual_pipeline_model_parallel_size: null # interleaved pipeline
          resume_from_checkpoint: null # manually set the checkpoint file to load from
        
          # model architecture
          encoder_seq_length: 2048
          max_position_embeddings: 2048
          num_layers: 12
          hidden_size: 768
          ffn_hidden_size: ${multiply:4, ${.hidden_size}}  # Transformer FFN hidden size. 4 * hidden_size.
          num_attention_heads: 12
          init_method_std: 0.023  # Standard deviation of the zero mean normal distribution used for weight initialization.')
          hidden_dropout: 0.1  # Dropout probability for hidden state transformer.
          kv_channels: null  # Projection weights dimension in multi-head attention. Set to hidden_size // num_attention_heads if null
          apply_query_key_layer_scaling: True # scale Q * K^T by 1 / layer-number.
          layernorm_epsilon: 1e-5
          make_vocab_size_divisible_by: 128 # Pad the vocab size to be divisible by this value for computation efficiency.
          pre_process: True # add embedding
          post_process: True # add pooler
          persist_layer_norm: True # Use of persistent fused layer norm kernel.
          gradient_as_bucket_view: True # Allocate gradients in a contiguous bucket to save memory (less fragmentation and buffer memory)
        
          # Fusion
          grad_div_ar_fusion: True # Fuse grad division into torch.distributed.all_reduce
          gradient_accumulation_fusion: True # Fuse weight gradient accumulation to GEMMs
          bias_activation_fusion: True # Use a kernel that fuses the bias addition from weight matrices with the subsequent activation function.
          bias_dropout_add_fusion: True # Use a kernel that fuses the bias addition, dropout and residual connection addition.
          masked_softmax_fusion: True # Use a kernel that fuses the attention softmax with it's mask.
        
          ## Activation Checkpointing
          activations_checkpoint_granularity: selective # 'selective' or 'full'
          activations_checkpoint_method: block # 'uniform', 'block'
          activations_checkpoint_num_layers: 0
          num_micro_batches_with_partial_activation_checkpoints: null
          activations_checkpoint_layers_per_pipeline: null 
        
          ## Sequence Parallelism
          sequence_parallel: False
        
          tokenizer:
            library: 'megatron'
            type: 'GPT2BPETokenizer'
            model: null
            delimiter: null # only used for tabular tokenizer
            vocab_file: ${data_dir}/bpe/vocab.json
            merge_file: ${data_dir}/bpe/merges.txt
        
          # precision
          native_amp_init_scale: 4294967296 # 2 ** 32
          native_amp_growth_interval: 1000
          hysteresis: 2 # Gradient scale hysteresis
          fp32_residual_connection: False # Move residual connections to fp32
          fp16_lm_cross_entropy: False # Move the cross entropy unreduced loss calculation for lm head to fp16
          
          # Megatron O2-style half-precision
          megatron_amp_O2: True # Enable O2-level automatic mixed precision using master parameters
          grad_allreduce_chunk_size_mb: 125
        
          ## Transformer Engine
          transformer_engine: False
          fp8: False # enables fp8 in TransformerLayer forward
          fp8_e4m3: False # sets fp8_format = recipe.Format.E4M3
          fp8_hybrid: False # sets fp8_format = recipe.Format.HYBRID
          fp8_margin: 0 # scaling margin
          fp8_interval: 1 # scaling update interval
          fp8_amax_history_len: 1 # Number of steps for which amax history is recorded per tensor
          fp8_amax_compute_algo: most_recent # 'most_recent' or 'max'. Algorithm for computing amax from history
          use_emha: False
        
          # miscellaneous
          seed: 1234
          sync_batch_comm: False
          use_cpu_initialization: False # Init weights on the CPU (slow for large models)
          onnx_safe: False # Use work-arounds for known problems with Torch ONNX exporter.
          apex_transformer_log_level: 30 # Python logging level displays logs with severity greater than or equal to this
        
          # Nsys profiling options
          nsys_profile:
            enabled: False
            trace: [nvtx,cuda]
            start_step: 10  # Global batch to start profiling
            end_step: 10 # Global batch to end profiling
            ranks: [0] # Global rank IDs to profile
            gen_shape: False # Generate model and kernel details including input shapes
        
          optim:
            name: distributed_fused_adam
            bucket_cap_mb: 200
            overlap_grad_sync: False
            contiguous_grad_buffer: True
            lr: 6e-4
            weight_decay: 0.1 
            betas: 
            - 0.9
            - 0.95
            sched:
              name: CosineAnnealing
              warmup_steps: 636
              constant_steps: 100000
              min_lr: 6e-5
        
          data:
            data_impl: mmap
            splits_string: "99990,8,2"
            seq_length: 2048
            skip_warmup: True
            num_workers: 2
            dataloader_type: single # cyclic
            reset_position_ids: False # Reset position ids after end-of-document token
            reset_attention_mask: False # Reset attention mask after end-of-document token
            eod_mask_loss: False # Mask loss for the end of document tokens
            index_mapping_dir: null # path to save index mapping .npy files, by default will save in the same location as data_prefix
            data_prefix: # Should be weight path weight path... for a blended dataset
              - .0333
              - ${data_dir}/my-gpt3_00_text_document
              - .0333
              - ${data_dir}/my-gpt3_01_text_document
              - .0333
              - ${data_dir}/my-gpt3_02_text_document
              - .0333
              - ${data_dir}/my-gpt3_03_text_document
              - .0333
              - ${data_dir}/my-gpt3_04_text_document
              - .0333
              - ${data_dir}/my-gpt3_05_text_document
              - .0333
              - ${data_dir}/my-gpt3_06_text_document
              - .0333
              - ${data_dir}/my-gpt3_07_text_document
              - .0333
              - ${data_dir}/my-gpt3_08_text_document
              - .0333
              - ${data_dir}/my-gpt3_09_text_document
              - .0333
              - ${data_dir}/my-gpt3_10_text_document
              - .0333
              - ${data_dir}/my-gpt3_11_text_document
              - .0333
              - ${data_dir}/my-gpt3_12_text_document
              - .0333
              - ${data_dir}/my-gpt3_13_text_document
              - .0333
              - ${data_dir}/my-gpt3_14_text_document
              - .0333
              - ${data_dir}/my-gpt3_15_text_document
              - .0333
              - ${data_dir}/my-gpt3_16_text_document
              - .0333
              - ${data_dir}/my-gpt3_17_text_document
              - .0333
              - ${data_dir}/my-gpt3_18_text_document
              - .0333
              - ${data_dir}/my-gpt3_19_text_document
              - .0333
              - ${data_dir}/my-gpt3_20_text_document
              - .0333
              - ${data_dir}/my-gpt3_21_text_document
              - .0333
              - ${data_dir}/my-gpt3_22_text_document
              - .0333
              - ${data_dir}/my-gpt3_23_text_document
              - .0333
              - ${data_dir}/my-gpt3_24_text_document
              - .0333
              - ${data_dir}/my-gpt3_25_text_document
              - .0333
              - ${data_dir}/my-gpt3_26_text_document
              - .0333
              - ${data_dir}/my-gpt3_27_text_document
              - .0333
              - ${data_dir}/my-gpt3_28_text_document
              - .0334
              - ${data_dir}/my-gpt3_29_text_document
        """
        expected = OmegaConf.create(s)
        assert (
            expected == conf
        ), f"conf/training/gpt3/126m.yaml must be set to {expected} but it currently is {conf}."

    def test_training_config_5b(self):
        conf = OmegaConf.load("conf/training/gpt3/5b.yaml")
        s = """
        run:
          name: gpt3_5b
          results_dir: ${base_results_dir}/${.name}
          time_limit: "6-00:00:00"
          dependency: "singleton"
        
        trainer:
          num_nodes: 16
          devices: 8
          accelerator: gpu
          precision: bf16
          logger: False # logger provided by exp_manager
          enable_checkpointing: False
          replace_sampler_ddp: False
          max_epochs: null
          max_steps: 75000 # consumed_samples = global_step * global_batch_size
          max_time: "05:23:30:00"
          log_every_n_steps: 10
          val_check_interval: 2000
          limit_val_batches: 50
          limit_test_batches: 50
          accumulate_grad_batches: 1
          gradient_clip_val: 1.0
        
        exp_manager:
          explicit_log_dir: ${training.run.results_dir}/results
          exp_dir: null
          name: megatron_gpt
          create_wandb_logger: False
          wandb_logger_kwargs:
            project: nemo_gpt3
            name: ${training.run.name}
          resume_if_exists: True
          resume_ignore_no_checkpoint: True
          create_checkpoint_callback: True
          checkpoint_callback_params:
            monitor: val_loss
            save_top_k: 10
            mode: min
            always_save_nemo: False # saves nemo file during validation, not implemented for model parallel
            save_nemo_on_train_end: False # not recommended when training large models on clusters with short time limits
            filename: 'megatron_gpt--{val_loss:.2f}-{step}-{consumed_samples}'
            model_parallel_size: ${multiply:${training.model.tensor_model_parallel_size}, ${training.model.pipeline_model_parallel_size}}
          log_step_timing: True
          step_timing_kwargs:
            sync_cuda: True
            buffer_size: 5
        
        model:
          # model parallelism: MBS=2, TPS=2, AGB=8 for 80GB nodes. 
          micro_batch_size: 2
          global_batch_size: 2048
          tensor_model_parallel_size: 1
          pipeline_model_parallel_size: 1
          virtual_pipeline_model_parallel_size: null # interleaved pipeline
          resume_from_checkpoint: null # manually set the checkpoint file to load from
        
          # model architecture
          encoder_seq_length: 2048
          max_position_embeddings: 2048
          num_layers: 24
          hidden_size: 4096
          ffn_hidden_size: ${multiply:4, ${.hidden_size}}  # Transformer FFN hidden size. 4 * hidden_size.
          num_attention_heads: 32
          init_method_std: 0.01  # Standard deviation of the zero mean normal distribution used for weight initialization.')
          hidden_dropout: 0.1  # Dropout probability for hidden state transformer.
          kv_channels: null  # Projection weights dimension in multi-head attention. Set to hidden_size // num_attention_heads if null
          apply_query_key_layer_scaling: True # scale Q * K^T by 1 / layer-number.
          layernorm_epsilon: 1e-5
          make_vocab_size_divisible_by: 128 # Pad the vocab size to be divisible by this value for computation efficiency.
          pre_process: True # add embedding
          post_process: True # add pooler
          persist_layer_norm: True # Use of persistent fused layer norm kernel.
          gradient_as_bucket_view: True # Allocate gradients in a contiguous bucket to save memory (less fragmentation and buffer memory)
        
          # Fusion
          grad_div_ar_fusion: True # Fuse grad division into torch.distributed.all_reduce
          gradient_accumulation_fusion: True # Fuse weight gradient accumulation to GEMMs
          bias_activation_fusion: True # Use a kernel that fuses the bias addition from weight matrices with the subsequent activation function.
          bias_dropout_add_fusion: True # Use a kernel that fuses the bias addition, dropout and residual connection addition.
          masked_softmax_fusion: True # Use a kernel that fuses the attention softmax with it's mask.
        
          ## Activation Checkpointing
          activations_checkpoint_granularity: selective # 'selective' or 'full'
          activations_checkpoint_method: block # 'uniform', 'block'
          activations_checkpoint_num_layers: 0 
          num_micro_batches_with_partial_activation_checkpoints: null
          activations_checkpoint_layers_per_pipeline: null 
          
          ## Sequence Parallelism
          sequence_parallel: False
        
          tokenizer:
            library: 'megatron'
            type: 'GPT2BPETokenizer'
            model: null
            delimiter: null # only used for tabular tokenizer
            vocab_file: ${data_dir}/bpe/vocab.json
            merge_file: ${data_dir}/bpe/merges.txt
        
          # precision
          native_amp_init_scale: 4294967296 # 2 ** 32
          native_amp_growth_interval: 1000
          hysteresis: 2 # Gradient scale hysteresis
          fp32_residual_connection: False # Move residual connections to fp32
          fp16_lm_cross_entropy: False # Move the cross entropy unreduced loss calculation for lm head to fp16
        
          # Megatron O2-style half-precision
          megatron_amp_O2: True # Enable O2-level automatic mixed precision using master parameters
          grad_allreduce_chunk_size_mb: 125
        
          ## Transformer Engine
          transformer_engine: False
          fp8: False # enables fp8 in TransformerLayer forward
          fp8_e4m3: False # sets fp8_format = recipe.Format.E4M3
          fp8_hybrid: False # sets fp8_format = recipe.Format.HYBRID
          fp8_margin: 0 # scaling margin
          fp8_interval: 1 # scaling update interval
          fp8_amax_history_len: 1 # Number of steps for which amax history is recorded per tensor
          fp8_amax_compute_algo: most_recent # 'most_recent' or 'max'. Algorithm for computing amax from history
          use_emha: False
        
          # miscellaneous
          seed: 1234
          sync_batch_comm: False
          use_cpu_initialization: False # Init weights on the CPU (slow for large models)
          onnx_safe: False # Use work-arounds for known problems with Torch ONNX exporter.
          apex_transformer_log_level: 30 # Python logging level displays logs with severity greater than or equal to this
        
          # Nsys profiling options
          nsys_profile:
            enabled: False
            trace: [nvtx,cuda]
            start_step: 10  # Global batch to start profiling
            end_step: 10 # Global batch to end profiling
            ranks: [0] # Global rank IDs to profile
            gen_shape: False # Generate model and kernel details including input shapes
        
          optim:
            name: distributed_fused_adam
            bucket_cap_mb: 200
            overlap_grad_sync: False
            contiguous_grad_buffer: True
            lr: 1.6e-4
            weight_decay: 0.1 
            betas: 
            - 0.9
            - 0.95
            sched:
              name: CosineAnnealing
              warmup_steps: 115
              constant_steps: 12500
              min_lr: 1.6e-5
        
          data:
            data_impl: mmap
            splits_string: "99990,8,2"
            seq_length: 2048
            skip_warmup: True
            num_workers: 2
            dataloader_type: single # cyclic
            reset_position_ids: False # Reset position ids after end-of-document token
            reset_attention_mask: False # Reset attention mask after end-of-document token
            eod_mask_loss: False # Mask loss for the end of document tokens
            index_mapping_dir: null # path to save index mapping .npy files, by default will save in the same location as data_prefix
            data_prefix: # Should be weight path weight path... for a blended dataset
              - .0333
              - ${data_dir}/my-gpt3_00_text_document
              - .0333
              - ${data_dir}/my-gpt3_01_text_document
              - .0333
              - ${data_dir}/my-gpt3_02_text_document
              - .0333
              - ${data_dir}/my-gpt3_03_text_document
              - .0333
              - ${data_dir}/my-gpt3_04_text_document
              - .0333
              - ${data_dir}/my-gpt3_05_text_document
              - .0333
              - ${data_dir}/my-gpt3_06_text_document
              - .0333
              - ${data_dir}/my-gpt3_07_text_document
              - .0333
              - ${data_dir}/my-gpt3_08_text_document
              - .0333
              - ${data_dir}/my-gpt3_09_text_document
              - .0333
              - ${data_dir}/my-gpt3_10_text_document
              - .0333
              - ${data_dir}/my-gpt3_11_text_document
              - .0333
              - ${data_dir}/my-gpt3_12_text_document
              - .0333
              - ${data_dir}/my-gpt3_13_text_document
              - .0333
              - ${data_dir}/my-gpt3_14_text_document
              - .0333
              - ${data_dir}/my-gpt3_15_text_document
              - .0333
              - ${data_dir}/my-gpt3_16_text_document
              - .0333
              - ${data_dir}/my-gpt3_17_text_document
              - .0333
              - ${data_dir}/my-gpt3_18_text_document
              - .0333
              - ${data_dir}/my-gpt3_19_text_document
              - .0333
              - ${data_dir}/my-gpt3_20_text_document
              - .0333
              - ${data_dir}/my-gpt3_21_text_document
              - .0333
              - ${data_dir}/my-gpt3_22_text_document
              - .0333
              - ${data_dir}/my-gpt3_23_text_document
              - .0333
              - ${data_dir}/my-gpt3_24_text_document
              - .0333
              - ${data_dir}/my-gpt3_25_text_document
              - .0333
              - ${data_dir}/my-gpt3_26_text_document
              - .0333
              - ${data_dir}/my-gpt3_27_text_document
              - .0333
              - ${data_dir}/my-gpt3_28_text_document
              - .0334
              - ${data_dir}/my-gpt3_29_text_document
        """
        expected = OmegaConf.create(s)
        assert (
            expected == conf
        ), f"conf/training/gpt3/5b.yaml must be set to {expected} but it currently is {conf}."

    def test_training_config_20b(self):
        conf = OmegaConf.load("conf/training/gpt3/20b.yaml")
        s = """
        run:
          name: gpt3_20b
          results_dir: ${base_results_dir}/${.name}
          time_limit: "7-00:00:00"
          dependency: "singleton"
        
        trainer:
          devices: 8
          num_nodes: 64
          accelerator: gpu
          precision: bf16
          logger: False # logger provided by exp_manager
          enable_checkpointing: False
          replace_sampler_ddp: False
          max_epochs: null
          max_steps: 75000 # consumed_samples = global_step * global_batch_size
          max_time: "06:23:30:00"
          log_every_n_steps: 10
          val_check_interval: 2000
          limit_val_batches: 50
          limit_test_batches: 50
          accumulate_grad_batches: 1
          gradient_clip_val: 1.0
        
        exp_manager:
          explicit_log_dir: ${training.run.results_dir}/results
          exp_dir: null
          name: megatron_gpt
          create_wandb_logger: False
          wandb_logger_kwargs:
            project: nemo_gpt3
            name: ${training.run.name}
          resume_if_exists: True
          resume_ignore_no_checkpoint: True
          create_checkpoint_callback: True
          checkpoint_callback_params:
            monitor: val_loss
            save_top_k: 10
            mode: min
            always_save_nemo: False # saves nemo file during validation, not implemented for model parallel
            save_nemo_on_train_end: False # not recommended when training large models on clusters with short time limits
            filename: 'megatron_gpt--{val_loss:.2f}-{step}-{consumed_samples}'
            model_parallel_size: ${multiply:${training.model.tensor_model_parallel_size}, ${training.model.pipeline_model_parallel_size}}
          log_step_timing: True
          step_timing_kwargs:
            sync_cuda: True
            buffer_size: 5
        
        model:
          micro_batch_size: 2
          global_batch_size: 2048
          tensor_model_parallel_size: 4
          pipeline_model_parallel_size: 1
          virtual_pipeline_model_parallel_size: null # interleaved pipeline
          resume_from_checkpoint: null # manually set the checkpoint file to load from
        
          # model architecture
          encoder_seq_length: 2048
          max_position_embeddings: 2048
          num_layers: 44
          hidden_size: 6144
          ffn_hidden_size: ${multiply:4, ${.hidden_size}}  # Transformer FFN hidden size. 4 * hidden_size.
          num_attention_heads: 48
          init_method_std: 0.008165  # Standard deviation of the zero mean normal distribution used for weight initialization.')
          hidden_dropout: 0.1  # Dropout probability for hidden state transformer.
          kv_channels: null  # Projection weights dimension in multi-head attention. Set to hidden_size // num_attention_heads if null
          apply_query_key_layer_scaling: True # scale Q * K^T by 1 / layer-number.
          layernorm_epsilon: 1e-5
          make_vocab_size_divisible_by: 128 # Pad the vocab size to be divisible by this value for computation efficiency.
          pre_process: True # add embedding
          post_process: True # add pooler
          persist_layer_norm: True # Use of persistent fused layer norm kernel.
          gradient_as_bucket_view: True # Allocate gradients in a contiguous bucket to save memory (less fragmentation and buffer memory)
        
          # Fusion
          grad_div_ar_fusion: True # Fuse grad division into torch.distributed.all_reduce
          gradient_accumulation_fusion: True # Fuse weight gradient accumulation to GEMMs
          bias_activation_fusion: True # Use a kernel that fuses the bias addition from weight matrices with the subsequent activation function.
          bias_dropout_add_fusion: True # Use a kernel that fuses the bias addition, dropout and residual connection addition.
          masked_softmax_fusion: True # Use a kernel that fuses the attention softmax with it's mask.
        
          ## Activation Checkpointing
          activations_checkpoint_granularity: selective # 'selective' or 'full'
          activations_checkpoint_method: block # 'uniform', 'block'
          activations_checkpoint_num_layers: 0
          num_micro_batches_with_partial_activation_checkpoints: null
          activations_checkpoint_layers_per_pipeline: null 

          ## Sequence Parallelism
          sequence_parallel: True
        
          tokenizer:
            library: 'megatron'
            type: 'GPT2BPETokenizer'
            model: null
            delimiter: null # only used for tabular tokenizer
            vocab_file: ${data_dir}/bpe/vocab.json
            merge_file: ${data_dir}/bpe/merges.txt
        
          # precision
          native_amp_init_scale: 4294967296 # 2 ** 32
          native_amp_growth_interval: 1000
          hysteresis: 2 # Gradient scale hysteresis
          fp32_residual_connection: False # Move residual connections to fp32
          fp16_lm_cross_entropy: False # Move the cross entropy unreduced loss calculation for lm head to fp16
          
          # Megatron O2-style half-precision
          megatron_amp_O2: True # Enable O2-level automatic mixed precision using master parameters
          grad_allreduce_chunk_size_mb: 125
        
          ## Transformer Engine
          transformer_engine: False
          fp8: False # enables fp8 in TransformerLayer forward
          fp8_e4m3: False # sets fp8_format = recipe.Format.E4M3
          fp8_hybrid: False # sets fp8_format = recipe.Format.HYBRID
          fp8_margin: 0 # scaling margin
          fp8_interval: 1 # scaling update interval
          fp8_amax_history_len: 1 # Number of steps for which amax history is recorded per tensor
          fp8_amax_compute_algo: most_recent # 'most_recent' or 'max'. Algorithm for computing amax from history
          use_emha: False
        
          # miscellaneous
          seed: 1234
          sync_batch_comm: False
          use_cpu_initialization: False # Init weights on the CPU (slow for large models)
          onnx_safe: False # Use work-arounds for known problems with Torch ONNX exporter.
          apex_transformer_log_level: 30 # Python logging level displays logs with severity greater than or equal to this
        
          # Nsys profiling options
          nsys_profile:
            enabled: False
            trace: [nvtx,cuda]
            start_step: 10  # Global batch to start profiling
            end_step: 10 # Global batch to end profiling
            ranks: [0] # Global rank IDs to profile
            gen_shape: False # Generate model and kernel details including input shapes
        
          optim:
            name: distributed_fused_adam
            bucket_cap_mb: 200
            overlap_grad_sync: False
            contiguous_grad_buffer: True
            lr: 1.4e-4
            weight_decay: 0.1 
            betas: 
            - 0.9
            - 0.95
            sched:
              name: CosineAnnealing
              warmup_steps: 115
              constant_steps: 12500
              min_lr: 1.4e-5
        
          data:
            data_impl: mmap
            splits_string: "99990,8,2"
            seq_length: 2048
            skip_warmup: True
            num_workers: 2
            dataloader_type: single # cyclic
            reset_position_ids: False # Reset position ids after end-of-document token
            reset_attention_mask: False # Reset attention mask after end-of-document token
            eod_mask_loss: False # Mask loss for the end of document tokens
            index_mapping_dir: null # path to save index mapping .npy files, by default will save in the same location as data_prefix
            data_prefix: # Should be weight path weight path... for a blended dataset
              - .0333
              - ${data_dir}/my-gpt3_00_text_document
              - .0333
              - ${data_dir}/my-gpt3_01_text_document
              - .0333
              - ${data_dir}/my-gpt3_02_text_document
              - .0333
              - ${data_dir}/my-gpt3_03_text_document
              - .0333
              - ${data_dir}/my-gpt3_04_text_document
              - .0333
              - ${data_dir}/my-gpt3_05_text_document
              - .0333
              - ${data_dir}/my-gpt3_06_text_document
              - .0333
              - ${data_dir}/my-gpt3_07_text_document
              - .0333
              - ${data_dir}/my-gpt3_08_text_document
              - .0333
              - ${data_dir}/my-gpt3_09_text_document
              - .0333
              - ${data_dir}/my-gpt3_10_text_document
              - .0333
              - ${data_dir}/my-gpt3_11_text_document
              - .0333
              - ${data_dir}/my-gpt3_12_text_document
              - .0333
              - ${data_dir}/my-gpt3_13_text_document
              - .0333
              - ${data_dir}/my-gpt3_14_text_document
              - .0333
              - ${data_dir}/my-gpt3_15_text_document
              - .0333
              - ${data_dir}/my-gpt3_16_text_document
              - .0333
              - ${data_dir}/my-gpt3_17_text_document
              - .0333
              - ${data_dir}/my-gpt3_18_text_document
              - .0333
              - ${data_dir}/my-gpt3_19_text_document
              - .0333
              - ${data_dir}/my-gpt3_20_text_document
              - .0333
              - ${data_dir}/my-gpt3_21_text_document
              - .0333
              - ${data_dir}/my-gpt3_22_text_document
              - .0333
              - ${data_dir}/my-gpt3_23_text_document
              - .0333
              - ${data_dir}/my-gpt3_24_text_document
              - .0333
              - ${data_dir}/my-gpt3_25_text_document
              - .0333
              - ${data_dir}/my-gpt3_26_text_document
              - .0333
              - ${data_dir}/my-gpt3_27_text_document
              - .0333
              - ${data_dir}/my-gpt3_28_text_document
              - .0334
              - ${data_dir}/my-gpt3_29_text_document
        """
        expected = OmegaConf.create(s)
        assert (
            expected == conf
        ), f"conf/training/gpt3/20b.yaml must be set to {expected} but it currently is {conf}."

    def test_training_config_40b(self):
        conf = OmegaConf.load("conf/training/gpt3/40b.yaml")
        s = """
        run:
          name: gpt3_40b
          results_dir: ${base_results_dir}/${.name}
          time_limit: "6-12:00:00"
          dependency: "singleton"
        
        trainer:
          num_nodes: 128
          devices: 8
          accelerator: gpu
          precision: bf16
          logger: False # logger provided by exp_manager
          enable_checkpointing: False
          replace_sampler_ddp: False
          max_epochs: null
          max_steps: 75000 # consumed_samples = global_step * global_batch_size
          max_time: "6:11:00:00"
          log_every_n_steps: 10
          val_check_interval: 2000
          limit_val_batches: 20
          limit_test_batches: 20
          accumulate_grad_batches: 1
          gradient_clip_val: 1.0
        
        exp_manager:
          explicit_log_dir: ${training.run.results_dir}/results
          exp_dir: null
          name: megatron_gpt
          create_wandb_logger: False
          wandb_logger_kwargs:
            project: nemo_gpt3
            name: ${training.run.name}
          resume_if_exists: True
          resume_ignore_no_checkpoint: True
          create_checkpoint_callback: True
          checkpoint_callback_params:
            monitor: val_loss
            save_top_k: 5
            mode: min
            always_save_nemo: False # saves nemo file during validation, not implemented for model parallel
            save_nemo_on_train_end: False # not recommended when training large models on clusters with short time limits
            filename: 'megatron_gpt--{val_loss:.2f}-{step}-{consumed_samples}'
            model_parallel_size: ${multiply:${training.model.tensor_model_parallel_size}, ${training.model.pipeline_model_parallel_size}}
          log_step_timing: True
          step_timing_kwargs:
            sync_cuda: True
            buffer_size: 5
        
        model:
          micro_batch_size: 2
          global_batch_size: 2048
          tensor_model_parallel_size: 8
          pipeline_model_parallel_size: 1
          virtual_pipeline_model_parallel_size: null # interleaved pipeline
          resume_from_checkpoint: null # manually set the checkpoint file to load from
        
          # model architecture
          encoder_seq_length: 2048
          max_position_embeddings: 2048
          num_layers: 48
          hidden_size: 8192
          ffn_hidden_size: ${multiply:4, ${.hidden_size}}  # Transformer FFN hidden size. 4 * hidden_size.
          num_attention_heads: 64
          init_method_std: 0.007  # Standard deviation of the zero mean normal distribution used for weight initialization.')
          hidden_dropout: 0.1  # Dropout probability for hidden state transformer.
          kv_channels: null  # Projection weights dimension in multi-head attention. Set to hidden_size // num_attention_heads if null
          apply_query_key_layer_scaling: True # scale Q * K^T by 1 / layer-number.
          layernorm_epsilon: 1e-5
          make_vocab_size_divisible_by: 128 # Pad the vocab size to be divisible by this value for computation efficiency.
          pre_process: True # add embedding
          post_process: True # add pooler
          persist_layer_norm: True # Use of persistent fused layer norm kernel.
          gradient_as_bucket_view: True # Allocate gradients in a contiguous bucket to save memory (less fragmentation and buffer memory)
        
          # Fusion
          grad_div_ar_fusion: True # Fuse grad division into torch.distributed.all_reduce
          gradient_accumulation_fusion: True # Fuse weight gradient accumulation to GEMMs
          bias_activation_fusion: True # Use a kernel that fuses the bias addition from weight matrices with the subsequent activation function.
          bias_dropout_add_fusion: True # Use a kernel that fuses the bias addition, dropout and residual connection addition.
          masked_softmax_fusion: True # Use a kernel that fuses the attention softmax with it's mask.
        
          ## Activation Checkpointing
          activations_checkpoint_granularity: selective # 'selective' or 'full'
          activations_checkpoint_method: block # 'uniform', 'block'
          activations_checkpoint_num_layers: 0
          num_micro_batches_with_partial_activation_checkpoints: null
          activations_checkpoint_layers_per_pipeline: null 

          ## Sequence Parallelism
          sequence_parallel: True
        
          tokenizer:
            library: 'megatron'
            type: 'GPT2BPETokenizer'
            model: null
            delimiter: null # only used for tabular tokenizer
            vocab_file: ${data_dir}/bpe/vocab.json
            merge_file: ${data_dir}/bpe/merges.txt
        
          # precision
          native_amp_init_scale: 4294967296 # 2 ** 32
          native_amp_growth_interval: 1000
          hysteresis: 2 # Gradient scale hysteresis
          fp32_residual_connection: False # Move residual connections to fp32
          fp16_lm_cross_entropy: False # Move the cross entropy unreduced loss calculation for lm head to fp16
        
          # Megatron O2-style half-precision
          megatron_amp_O2: True # Enable O2-level automatic mixed precision using master parameters
          grad_allreduce_chunk_size_mb: 125
        
          ## Transformer Engine
          transformer_engine: False
          fp8: False # enables fp8 in TransformerLayer forward
          fp8_e4m3: False # sets fp8_format = recipe.Format.E4M3
          fp8_hybrid: False # sets fp8_format = recipe.Format.HYBRID
          fp8_margin: 0 # scaling margin
          fp8_interval: 1 # scaling update interval
          fp8_amax_history_len: 1 # Number of steps for which amax history is recorded per tensor
          fp8_amax_compute_algo: most_recent # 'most_recent' or 'max'. Algorithm for computing amax from history
          use_emha: False
        
          # miscellaneous
          seed: 1234
          sync_batch_comm: False
          use_cpu_initialization: False # Init weights on the CPU (slow for large models)
          onnx_safe: False # Use work-arounds for known problems with Torch ONNX exporter.
          apex_transformer_log_level: 30 # Python logging level displays logs with severity greater than or equal to this
        
          # Nsys profiling options
          nsys_profile:
            enabled: False
            trace: [nvtx,cuda]
            start_step: 10  # Global batch to start profiling
            end_step: 10 # Global batch to end profiling
            ranks: [0] # Global rank IDs to profile
            gen_shape: False # Generate model and kernel details including input shapes
        
          optim:
            name: distributed_fused_adam
            bucket_cap_mb: 200
            overlap_grad_sync: False
            contiguous_grad_buffer: True
            lr: 1.1e-4
            weight_decay: 0.1 
            betas: 
            - 0.9
            - 0.95
            sched:
              name: CosineAnnealing
              warmup_steps: 115
              constant_steps: 12500
              min_lr: 1.1e-5
        
          data:
            data_impl: mmap
            splits_string: "99990,8,2"
            seq_length: 2048
            skip_warmup: True
            num_workers: 2
            dataloader_type: single # cyclic
            reset_position_ids: False # Reset position ids after end-of-document token
            reset_attention_mask: False # Reset attention mask after end-of-document token
            eod_mask_loss: False # Mask loss for the end of document tokens
            index_mapping_dir: null # path to save index mapping .npy files, by default will save in the same location as data_prefix
            data_prefix: # Should be weight path weight path... for a blended dataset
              - .0333
              - ${data_dir}/my-gpt3_00_text_document
              - .0333
              - ${data_dir}/my-gpt3_01_text_document
              - .0333
              - ${data_dir}/my-gpt3_02_text_document
              - .0333
              - ${data_dir}/my-gpt3_03_text_document
              - .0333
              - ${data_dir}/my-gpt3_04_text_document
              - .0333
              - ${data_dir}/my-gpt3_05_text_document
              - .0333
              - ${data_dir}/my-gpt3_06_text_document
              - .0333
              - ${data_dir}/my-gpt3_07_text_document
              - .0333
              - ${data_dir}/my-gpt3_08_text_document
              - .0333
              - ${data_dir}/my-gpt3_09_text_document
              - .0333
              - ${data_dir}/my-gpt3_10_text_document
              - .0333
              - ${data_dir}/my-gpt3_11_text_document
              - .0333
              - ${data_dir}/my-gpt3_12_text_document
              - .0333
              - ${data_dir}/my-gpt3_13_text_document
              - .0333
              - ${data_dir}/my-gpt3_14_text_document
              - .0333
              - ${data_dir}/my-gpt3_15_text_document
              - .0333
              - ${data_dir}/my-gpt3_16_text_document
              - .0333
              - ${data_dir}/my-gpt3_17_text_document
              - .0333
              - ${data_dir}/my-gpt3_18_text_document
              - .0333
              - ${data_dir}/my-gpt3_19_text_document
              - .0333
              - ${data_dir}/my-gpt3_20_text_document
              - .0333
              - ${data_dir}/my-gpt3_21_text_document
              - .0333
              - ${data_dir}/my-gpt3_22_text_document
              - .0333
              - ${data_dir}/my-gpt3_23_text_document
              - .0333
              - ${data_dir}/my-gpt3_24_text_document
              - .0333
              - ${data_dir}/my-gpt3_25_text_document
              - .0333
              - ${data_dir}/my-gpt3_26_text_document
              - .0333
              - ${data_dir}/my-gpt3_27_text_document
              - .0333
              - ${data_dir}/my-gpt3_28_text_document
              - .0334
              - ${data_dir}/my-gpt3_29_text_document
        """
        expected = OmegaConf.create(s)
        assert (
            expected == conf
        ), f"conf/training/gpt3/40b.yaml must be set to {expected} but it currently is {conf}."

    def test_training_config_175b(self):
        conf = OmegaConf.load("conf/training/gpt3/175b.yaml")
        s = """
        run:
          name: gpt3_175b
          results_dir: ${base_results_dir}/${.name}
          time_limit: "26-00:00:00"
          dependency: "singleton"
        
        trainer:
          num_nodes: 128
          devices: 8
          accelerator: gpu
          precision: bf16
          logger: False # logger provided by exp_manager
          enable_checkpointing: False
          replace_sampler_ddp: False
          max_epochs: null
          max_steps: 75000 # consumed_samples = global_step * global_batch_size
          max_time: "25:23:00:00"
          log_every_n_steps: 10
          val_check_interval: 2000
          limit_val_batches: 20
          limit_test_batches: 20
          accumulate_grad_batches: 1
          gradient_clip_val: 1.0
        
        exp_manager:
          explicit_log_dir: ${training.run.results_dir}/results
          exp_dir: null
          name: megatron_gpt
          create_wandb_logger: False
          wandb_logger_kwargs:
            project: nemo_gpt3
            name: ${training.run.name}
          resume_if_exists: True
          resume_ignore_no_checkpoint: True
          create_checkpoint_callback: True
          checkpoint_callback_params:
            monitor: val_loss
            save_top_k: 5
            mode: min
            always_save_nemo: False # saves nemo file during validation, not implemented for model parallel
            save_nemo_on_train_end: False # not recommended when training large models on clusters with short time limits
            filename: 'megatron_gpt--{val_loss:.2f}-{step}-{consumed_samples}'
            model_parallel_size: ${multiply:${training.model.tensor_model_parallel_size}, ${training.model.pipeline_model_parallel_size}}
          log_step_timing: True
          step_timing_kwargs:
            sync_cuda: True
            buffer_size: 5
        
        model:
          micro_batch_size: 1
          global_batch_size: 2048
          tensor_model_parallel_size: 8
          pipeline_model_parallel_size: 16
          virtual_pipeline_model_parallel_size: 6 # interleaved pipeline
          resume_from_checkpoint: null # manually set the checkpoint file to load from
        
          # model architecture
          encoder_seq_length: 2048
          max_position_embeddings: 2048
          num_layers: 96
          hidden_size: 12288
          ffn_hidden_size: ${multiply:4, ${.hidden_size}}  # Transformer FFN hidden size. 4 * hidden_size.
          num_attention_heads: 96
          init_method_std: 0.006  # Standard deviation of the zero mean normal distribution used for weight initialization.')
          hidden_dropout: 0.1  # Dropout probability for hidden state transformer.
          kv_channels: null  # Projection weights dimension in multi-head attention. Set to hidden_size // num_attention_heads if null
          apply_query_key_layer_scaling: True # scale Q * K^T by 1 / layer-number.
          layernorm_epsilon: 1e-5
          make_vocab_size_divisible_by: 128 # Pad the vocab size to be divisible by this value for computation efficiency.
          pre_process: True # add embedding
          post_process: True # add pooler
          persist_layer_norm: True # Use of persistent fused layer norm kernel.
          gradient_as_bucket_view: True # Allocate gradients in a contiguous bucket to save memory (less fragmentation and buffer memory)
        
          # Fusion
          grad_div_ar_fusion: True # Fuse grad division into torch.distributed.all_reduce
          gradient_accumulation_fusion: True # Fuse weight gradient accumulation to GEMMs
          bias_activation_fusion: True # Use a kernel that fuses the bias addition from weight matrices with the subsequent activation function.
          bias_dropout_add_fusion: True # Use a kernel that fuses the bias addition, dropout and residual connection addition.
          masked_softmax_fusion: True # Use a kernel that fuses the attention softmax with it's mask.
        
          ## Activation Checkpointing
          activations_checkpoint_granularity: selective # 'selective' or 'full'
          activations_checkpoint_method: block # 'uniform', 'block'
          activations_checkpoint_num_layers: 0
          num_micro_batches_with_partial_activation_checkpoints: 108
          activations_checkpoint_layers_per_pipeline: 0

          ## Sequence Parallelism
          sequence_parallel: True
        
          tokenizer:
            library: 'megatron'
            type: 'GPT2BPETokenizer'
            model: null
            delimiter: null # only used for tabular tokenizer
            vocab_file: ${data_dir}/bpe/vocab.json
            merge_file: ${data_dir}/bpe/merges.txt
        
          # precision
          native_amp_init_scale: 4294967296 # 2 ** 32
          native_amp_growth_interval: 1000
          hysteresis: 2 # Gradient scale hysteresis
          fp32_residual_connection: False # Move residual connections to fp32
          fp16_lm_cross_entropy: False # Move the cross entropy unreduced loss calculation for lm head to fp16
        
          # Megatron O2-style half-precision
          megatron_amp_O2: True # Enable O2-level automatic mixed precision using master parameters
          grad_allreduce_chunk_size_mb: 125
        
          ## Transformer Engine
          transformer_engine: False
          fp8: False # enables fp8 in TransformerLayer forward
          fp8_e4m3: False # sets fp8_format = recipe.Format.E4M3
          fp8_hybrid: False # sets fp8_format = recipe.Format.HYBRID
          fp8_margin: 0 # scaling margin
          fp8_interval: 1 # scaling update interval
          fp8_amax_history_len: 1 # Number of steps for which amax history is recorded per tensor
          fp8_amax_compute_algo: most_recent # 'most_recent' or 'max'. Algorithm for computing amax from history
          use_emha: False
        
          # miscellaneous
          seed: 1234
          sync_batch_comm: False
          use_cpu_initialization: False # Init weights on the CPU (slow for large models)
          onnx_safe: False # Use work-arounds for known problems with Torch ONNX exporter.
          apex_transformer_log_level: 30 # Python logging level displays logs with severity greater than or equal to this
        
          # Nsys profiling options
          nsys_profile:
            enabled: False
            trace: [nvtx,cuda]
            start_step: 10  # Global batch to start profiling
            end_step: 10 # Global batch to end profiling
            ranks: [0] # Global rank IDs to profile
            gen_shape: False # Generate model and kernel details including input shapes
        
          optim:
            name: distributed_fused_adam
            bucket_cap_mb: 200
            overlap_grad_sync: False
            contiguous_grad_buffer: True
            lr: 0.9e-4
            weight_decay: 0.1 
            betas: 
            - 0.9
            - 0.95
            sched:
              name: CosineAnnealing
              warmup_steps: 115
              constant_steps: 12500
              min_lr: 0.9e-5
        
          data:
            data_impl: mmap
            splits_string: "99990,8,2"
            seq_length: 2048
            skip_warmup: True
            num_workers: 2
            dataloader_type: single # cyclic
            reset_position_ids: False # Reset position ids after end-of-document token
            reset_attention_mask: False # Reset attention mask after end-of-document token
            eod_mask_loss: False # Mask loss for the end of document tokens
            index_mapping_dir: null # path to save index mapping .npy files, by default will save in the same location as data_prefix
            data_prefix: # Should be weight path weight path... for a blended dataset
              - .0333
              - ${data_dir}/my-gpt3_00_text_document
              - .0333
              - ${data_dir}/my-gpt3_01_text_document
              - .0333
              - ${data_dir}/my-gpt3_02_text_document
              - .0333
              - ${data_dir}/my-gpt3_03_text_document
              - .0333
              - ${data_dir}/my-gpt3_04_text_document
              - .0333
              - ${data_dir}/my-gpt3_05_text_document
              - .0333
              - ${data_dir}/my-gpt3_06_text_document
              - .0333
              - ${data_dir}/my-gpt3_07_text_document
              - .0333
              - ${data_dir}/my-gpt3_08_text_document
              - .0333
              - ${data_dir}/my-gpt3_09_text_document
              - .0333
              - ${data_dir}/my-gpt3_10_text_document
              - .0333
              - ${data_dir}/my-gpt3_11_text_document
              - .0333
              - ${data_dir}/my-gpt3_12_text_document
              - .0333
              - ${data_dir}/my-gpt3_13_text_document
              - .0333
              - ${data_dir}/my-gpt3_14_text_document
              - .0333
              - ${data_dir}/my-gpt3_15_text_document
              - .0333
              - ${data_dir}/my-gpt3_16_text_document
              - .0333
              - ${data_dir}/my-gpt3_17_text_document
              - .0333
              - ${data_dir}/my-gpt3_18_text_document
              - .0333
              - ${data_dir}/my-gpt3_19_text_document
              - .0333
              - ${data_dir}/my-gpt3_20_text_document
              - .0333
              - ${data_dir}/my-gpt3_21_text_document
              - .0333
              - ${data_dir}/my-gpt3_22_text_document
              - .0333
              - ${data_dir}/my-gpt3_23_text_document
              - .0333
              - ${data_dir}/my-gpt3_24_text_document
              - .0333
              - ${data_dir}/my-gpt3_25_text_document
              - .0333
              - ${data_dir}/my-gpt3_26_text_document
              - .0333
              - ${data_dir}/my-gpt3_27_text_document
              - .0333
              - ${data_dir}/my-gpt3_28_text_document
              - .0334
              - ${data_dir}/my-gpt3_29_text_document
        """
        expected = OmegaConf.create(s)
        assert (
            expected == conf
        ), f"conf/training/gpt3/175b.yaml must be set to {expected} but it currently is {conf}."
