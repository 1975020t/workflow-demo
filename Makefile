.PHONY: create.index
create.index:
	@uv run python -m src.scripts.create_index

.PHONY: delete.index
delete.index:
	@uv run python -m src.scripts.delete_index
