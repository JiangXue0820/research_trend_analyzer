# trend_tool.py
import re
import matplotlib.pyplot as plt

# Global data store for papers (list of Documents or dicts with metadata)
paper_data = []

def init_data(doc_list):
    """Initialize paper data for trend analysis (list of documents with metadata)."""
    global paper_data
    paper_data = doc_list

def analyze_trends(query: str):
    """Analyze research trends (e.g., topic popularity over years, top topics) based on the query."""
    if not paper_data:
        return "No paper data available for trend analysis."
    # Parse query for conference name and years
    conf_name = None
    years = re.findall(r"(19\d{2}|20\d{2})", query)  # find any 4-digit year
    years = [int(y) for y in years]
    if len(years) >= 2:
        start_year, end_year = min(years), max(years)
    elif len(years) == 1:
        start_year = end_year = years[0]
    else:
        # If no year specified, default to last 5 years present in data
        all_years = sorted({int(doc.metadata.get('year')) for doc in paper_data if 'year' in doc.metadata})
        if all_years:
            end_year = all_years[-1]
            start_year = max(all_years[0], end_year - 4)
        else:
            return "No year information in data."
    # Find conference acronym in query (assume conf names are uppercase acronyms like CVPR, ICML, etc.)
    tokens = query.split()
    for token in tokens:
        if token.isupper() and len(token) >= 3:
            conf_name = token
            break
    # Determine topic keywords by removing known parts (years, conf name, common words)
    skip_words = set([str(y) for y in years] + ["trend", "trends", "trending", "research", "papers", "topics", "topic"])
    if conf_name:
        skip_words.add(conf_name)
    topic_words = [t for t in tokens if t.lower() not in skip_words and t.upper() != conf_name]
    topic = " ".join(topic_words).strip().lower()
    # Filter papers by conference (if specified) and year range
    selected_docs = []
    for doc in paper_data:
        year = int(doc.metadata.get('year', 0)) if 'year' in doc.metadata else None
        conf = doc.metadata.get('conference', None)
        if not year or year < start_year or year > end_year:
            continue
        if conf_name:
            if conf and conf_name.lower() in conf.lower():
                selected_docs.append(doc)
        else:
            selected_docs.append(doc)
    if not selected_docs:
        return f"No papers found for the specified criteria (conference={conf_name}, years={start_year}-{end_year})."
    # If no specific topic is given, identify top topics in the selected docs
    if topic == "":
        text = " ".join([doc.metadata.get('title', '') + " " + doc.metadata.get('abstract', '') for doc in selected_docs])
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        # Filter out common stopwords for topic extraction
        stopwords = {"the", "and", "with", "from", "this", "that", "have", "will", "which", "also", "been", "into", "between", "using", "such"}
        freq = {}
        for w in words:
            if w in stopwords:
                continue
            freq[w] = freq.get(w, 0) + 1
        top_topics = sorted(freq, key=freq.get, reverse=True)[:5]
        if not top_topics:
            return "Could not determine trending topics."
        topic_summary = ", ".join(top_topics)
        return f"Top research topics from {start_year} to {end_year}{(' in ' + conf_name) if conf_name else ''}: {topic_summary}."
    else:
        # Analyze trend of the specified topic over the years
        year_counts = {}
        for yr in range(start_year, end_year + 1):
            # Filter papers for this year
            year_docs = [doc for doc in selected_docs if 'year' in doc.metadata and int(doc.metadata['year']) == yr]
            count = 0
            for doc in year_docs:
                content = (doc.metadata.get('title', '') + " " + doc.metadata.get('abstract', '')).lower()
                if topic and topic in content:
                    count += 1
            year_counts[yr] = count
        # Create a textual trend summary
        trend_text = f"Trend for '{topic}' from {start_year} to {end_year}"
        if conf_name:
            trend_text += f" in {conf_name}"
        trend_text += ":\n" + ", ".join([f"{yr}: {cnt} papers" for yr, cnt in sorted(year_counts.items())])
        # Optionally generate a chart if the query requests it
        if any(word in query.lower() for word in ["chart", "plot", "graph"]):
            img_path = generate_trend_chart(year_counts, topic, conf_name)
            trend_text += f"\nTrend chart saved as {img_path}."
        return trend_text

def generate_trend_chart(year_counts: dict, topic: str, conf_name=None):
    """Generate a line chart image for the trend and save to file."""
    years = sorted(year_counts.keys())
    counts = [year_counts[y] for y in years]
    plt.figure()
    plt.plot(years, counts, marker='o')
    title = f"Trend of '{topic}'" + (f" in {conf_name}" if conf_name else "")
    plt.title(title)
    plt.xlabel("Year")
    plt.ylabel("Number of papers")
    plt.tight_layout()
    img_filename = f"trend_{topic.replace(' ', '_')}.png"
    plt.savefig(img_filename)
    return img_filename
