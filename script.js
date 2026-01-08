fetch("data/books.json")
	.then(r => r.json())
	.then(renderPage);

function renderPage(books) {
	const header = document.getElementById("header")


	const title = document.createElement("span")
	title.className = "h1"
	title.textContent = document.title
	header.appendChild(title)

	const article = document.getElementById("works");
	books.forEach(book => {
		article.appendChild(renderBook(book));
	});
}

function renderBook(book) {
	const section = document.createElement("section");


	// Title
	const h2 = document.createElement("h2");
	h2.textContent = book.meta.title
	h2.id = book.meta.key
	section.appendChild(h2);

	const margin_anchor = document.createElement("p")
	section.appendChild(margin_anchor)


	const h2_subtitle = document.createElement("p");
	h2_subtitle.className = "h2subtitle";
	h2_subtitle.textContent = `by ${book.meta.authors}`;
	section.appendChild(h2_subtitle)




	// Right margin book cover 
	if (book.meta.cover_url) {

		const cover_img = document.createElement("span");
		cover_img.className = "marginnote";

		const img = document.createElement("img");
		img.src = book.meta.cover_url;
		img.alt = book.meta.title;

		cover_img.appendChild(img);
		margin_anchor.appendChild(cover_img);
	}

	// metadata in margin note

	const margin_meta = document.createElement("span");
	margin_meta.className = "marginnote";

	const metaLines = [
		metaLine("Authors", book.meta.authors),
		// metaLine("Query", book.query),
		// metaLine("Review date", book.review_date),
		// metaLine("Proposed by", book.proposer),
		metaLine("First published", book.meta.first_publish_year),
		metaLine("Edition count", book.meta.edition_count),
		metaLine("Pages", book.meta.number_of_pages_median),
		metaLine("Subjects", book.meta.subjects),
		metaLine("Places", join(book.meta.place)),
		metaLine("Time", join(book.meta.time)),
		metaLine("OpenLibrary key", `<a href=https://openlibrary.org${book.meta.key}><code>${book.meta.key.replace("/works/", "")}</code></a>`),
		metaLine(
			"Wikidata IDs",
			(book.meta.id_wikidata || [])
				.map(id => `<a href="https://www.wikidata.org/wiki/${id}"><code>${id}</code></a>`)
				.join(", ")
		)

	];

	margin_meta.innerHTML = metaLines.join("");

	margin_anchor.appendChild(margin_meta);


	// first sentence epigraph
	if (book.meta.first_sentence) {
		const fs_div = document.createElement("div")
		fs_div.className = "epigraph"
		const fs_blockquote = document.createElement("blockquote")
		const fs_text = document.createElement("p")
		fs_text.textContent = book.meta.first_sentence
		// const fs_footer = document.createElement("footer")
		// fs_footer.textContent = `first sentence`
		fs_blockquote.appendChild(fs_text)
		// fs_blockquote.appendChild(fs_footer)
		fs_div.appendChild(fs_blockquote)
		section.appendChild(fs_div)
	}







	// Description (Markdown)
	if (book.meta.description) {
		const desc = document.createElement("p");
		desc.innerHTML = marked.parse(book.meta.description);
		section.appendChild(desc);
	}

	const ratings_table = createRatingsTable(book.ratings)
	if (ratings_table) {
		const ratings_title = document.createElement("h3")
		ratings_title.textContent = "Ratings"

		section.appendChild(ratings_title)
		ratings_table.className = "latex-table"
		const ratings_table_holder = document.createElement("p")
		ratings_table_holder.appendChild(ratings_table)
		section.appendChild(ratings_table_holder)

	}



	return section;
}

function metaLine(key, value) {
	return value ? `<strong>${key}:</strong> ${value}<br>` : "";
}

function join(v) {
	return Array.isArray(v) ? v.join(", ") : v;
}



function createRatingsTable(ratings) {
	/**
 * Creates an HTML table for given ratings.
 * @param {Object} ratings - Object where keys are raters and values are ratings
 * @returns {HTMLTableElement|null} - Table element if ratings exist, otherwise null
 */
	if (!ratings || Object.keys(ratings).length === 0) {
		return null; // no ratings, return null
	}

	const table = document.createElement("table");
	table.style.borderCollapse = "collapse";
	table.style.marginBottom = "1rem";

	// First row: rater names
	const headerRow = document.createElement("tr");
	for (const rater in ratings) {
		const th = document.createElement("th");
		th.innerText = rater;
		th.style.border = "1px solid #ccc";
		th.style.padding = "0.5rem";
		headerRow.appendChild(th);
	}
	table.appendChild(headerRow);

	// Second row: ratings
	const ratingRow = document.createElement("tr");
	for (const rater in ratings) {
		const td = document.createElement("td");
		td.innerText = ratings[rater];
		td.style.border = "1px solid #ccc";
		td.style.padding = "0.5rem";
		ratingRow.appendChild(td);
	}
	table.appendChild(ratingRow);

	return table;
}