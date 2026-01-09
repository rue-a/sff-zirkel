Promise.all([
	fetch("data/club.json").then(r => r.json()),
	fetch("data/books.json").then(r => r.json())
])
	.then(([club, books]) => {
		console.log("Club:", club);
		renderPage(club, books);
	});

function renderPage(club, books) {
	const header = document.getElementById("header")


	document.title = club.name
	const title = document.createElement("span")
	title.className = "h1"
	title.textContent = document.title
	header.appendChild(title)

	const article = document.getElementById("works");
	books.forEach(book => {
		article.appendChild(renderBook(book, club));
	});
}

function renderBook(book, club) {
	console.log(`Printing book section for ${book.meta.title}`)

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

	// book review announcement
	const now = new Date();
	const review_date = new Date(book["review_date"])
	const review_date_string = review_date.toLocaleDateString('en', { month: 'short', day: 'numeric', year: 'numeric' });



	if (review_date > now) {
		const review_announcement_p = document.createElement("p")
		review_announcement_p.textContent = `${book.meta.title} will be reviewed on ${review_date_string}.`;
		section.appendChild(review_announcement_p)
	}



	// Ratings

	// const ratings_table = createRatingsTable(book.ratings, book.meta.title)
	// if (ratings_table) {


	// 	const ratings_title = document.createElement("h3")
	// 	ratings_title.textContent = "Ratings"
	// 	// ratings_title.className = "center"
	// 	section.appendChild(ratings_title)

	// 	if (review_date <= now) {
	// 		const average_rating = Math.round(Object.values(book.ratings).reduce((acc, val) => acc + val, 0) / Object.values(book.ratings).length * 10) / 10

	// 		review_announcement_p.textContent = `On ${review_date_string} ${book.meta.title} was rated by the ${club.name} with an average of ${average_rating} out of 10 points.`;
	// 		section.appendChild(review_announcement_p)
	// 	}

	// 	const ratings_table_holder = document.createElement("p")
	// 	ratings_table.classList.add("center")
	// 	ratings_table_holder.appendChild(ratings_table)
	// 	section.appendChild(ratings_table_holder)


	// }




	if (checkRatings(book.ratings, book.meta.title)) {


		if (review_date <= now) {


			const ratings_title = document.createElement("h3")
			ratings_title.textContent = "Ratings"
			section.appendChild(ratings_title)

			const average_rating = Math.round(Object.values(book.ratings).reduce((acc, val) => acc + val, 0) / Object.values(book.ratings).length * 10) / 10
			const margin_ratings = createMarginRatings(book.ratings)
			console.log(margin_ratings)
			const review_p = document.createElement("p")

			review_p.innerHTML = `${margin_ratings.outerHTML} On ${review_date_string} ${book.meta.title} was rated by the ${club.name} with an average of ${average_rating} out of 10 points.`;
			// review_p.appendChild(margin_ratings);
			section.appendChild(review_p)
		}
	}




	console.log("")
	return section;
}

function metaLine(key, value) {
	return value ? `<strong>${key}:</strong> ${value}<br>` : "";
}

function join(v) {
	return Array.isArray(v) ? v.join(", ") : v;
}


function checkRatings(ratings, title) {
	// check for ratings object with content
	if (!ratings || Object.keys(ratings).length === 0) {
		console.warn(`No ratings found (${title}).`)
		return false; // no ratings, return null		
	}

	// only print ratings if everyone has rated the book
	for (let key of Object.keys(ratings)) {

		if (!(ratings[key])) {
			console.warn(`Not everyone has rated yet (${title}).`)
			return false
		}
		if (!(Number.isInteger(ratings[key]))) {
			console.warn(`Ratings contain non-integer values (${title}).`)
			return false
		}

	}
	return true
}


function createRatingsTable(ratings, title) {
	/**
 * Creates an HTML table for given ratings.
 * @param {Object} ratings - Object where keys are raters and values are ratings
 * @returns {HTMLTableElement|null} - Table element if ratings exist, otherwise null
 */





	// const average_rating = Math.round(Object.values(ratings).reduce((acc, val) => acc + val, 0) / Object.values(ratings).length * 10) / 10

	// ratings['Average'] = average_rating;

	const table = document.createElement("table");

	table.className = "latex-table"
	table.style.borderCollapse = "collapse";
	table.style.marginBottom = "1rem";

	// First row: rater names
	const headerRow = document.createElement("tr");
	for (const rater in ratings) {
		const th = document.createElement("th");
		th.innerText = rater;
		headerRow.appendChild(th);
	}
	table.appendChild(headerRow);

	// Second row: ratings
	const ratingRow = document.createElement("tr");
	for (const rater in ratings) {
		const td = document.createElement("td");
		td.innerText = ratings[rater];
		ratingRow.appendChild(td);
	}
	table.appendChild(ratingRow);

	return table;
}


function createMarginRatings(ratings) {

	const margin_ratings = document.createElement("span")
	margin_ratings.className = "marginnote";

	const metalines = [];
	for (let key of Object.keys(ratings)) {
		metalines.push(metaLine(key, ratings[key]));
	}

	margin_ratings.innerHTML = metalines.join("");
	return margin_ratings;

}