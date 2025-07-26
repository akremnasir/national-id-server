import sys
from id_generator import generate_id_card  # your main logic here

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    pdf_name = sys.argv[2]
    template_name = sys.argv[3]  # "Template 1" etc.

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result_buffer = generate_id_card(pdf_bytes, pdf_name, template_name)
    with open(f"generated/{result_buffer.name}", "wb") as out_file:
        out_file.write(result_buffer.getbuffer())

    print(result_buffer.name)  # Print output name to stdout for Node to capture
