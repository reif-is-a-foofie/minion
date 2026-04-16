# VM Install Notes

The transferred bundle works immediately as files and data.

To run semantic queries on the VM itself, the VM needs:

- Python with `pip`
- `numpy`
- `sentence-transformers`
- model availability for `sentence-transformers/all-MiniLM-L6-v2`

If the VM is intentionally lightweight, a valid alternative is:

- build the index locally
- store the bundle on the VM
- query it from a machine that already has the transformer stack

Current VM status when this bundle was prepared:

- `python3` present
- `pip` absent
- `numpy` absent
- `sentence_transformers` absent
