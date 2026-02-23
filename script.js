const points2grade = {
	15: "1<sup>+</sup>",
	14: "1",
	13: "1<sup>−</sup>",
	12: "2<sup>+</sup>",
	11: "2",
	10: "2<sup>−</sup>",
	9: "3<sup>+</sup>",
	8: "3",
	7: "3<sup>−</sup>",
	6: "4<sup>+</sup>",
	5: "4",
	4: "4<sup>−</sup>",
	3: "5<sup>+</sup>",
	2: "5",
	1: "5<sup>−</sup>",
	0: "6"
};



Promise.all([
	fetch("data/club.json").then(r => r.json()),
	fetch("data/books.json").then(r => r.json())
])
	.then(async ([club, books]) => {
		const popupRatings = await fetch(club.rating_popup).then(r => r.text());
		renderPage(club, books, popupRatings);
	});

function renderPage(club, books, popupRatings) {
	const popupHost = document.createElement("div");
	popupHost.innerHTML = popupRatings;
	const gradingPopup = popupHost.firstElementChild;
	gradingPopup.hidden = true;
	gradingPopup.style.position = "absolute";
	document.body.appendChild(gradingPopup);

	const header = document.getElementById("header")
	document.title = club.name
	const title = document.createElement("span")
	title.className = "h1"
	title.textContent = document.title
	header.appendChild(title)

	const article = document.getElementById("works");
	const sortedBooks = sortBooksByReviewDate(books);
	sortedBooks.forEach(book => {
		article.appendChild(renderBook(book, club, gradingPopup));
	});


}

function renderBook(book, club, gradingPopup) {
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
	const review_date_string = review_date.toLocaleDateString('en', { month: 'long', day: 'numeric', year: 'numeric' });



	const review_title = document.createElement("h3");
	review_title.textContent = "Review";
	section.appendChild(review_title);


	console.log(review_date)

	if (isNaN(review_date.getTime())) {
		const review_announcement_p = document.createElement("p")
		review_announcement_p.textContent = `A review date has not yet been set for ${book.meta.title}.`;
		section.appendChild(review_announcement_p)

		// don't print ratings yet, exit function
		return section
	}


	if (review_date > now) {
		const review_announcement_p = document.createElement("p")
		review_announcement_p.textContent = `${book.meta.title} will be reviewed on ${review_date_string}.`;
		section.appendChild(review_announcement_p)


		// don't print ratings yet, exit function
		return section
	}




	// Optional blocks. Only print ratings and review after the review date	

	if (ratings(book.ratings, book.meta.title)) {


		// section.appendChild(review_title);

		// Average rating
		const average_rating =
			Math.round(
				Object.values(book.ratings).reduce((acc, val) => acc + val, 0) /
				Object.values(book.ratings).length
			);





		// Create hover question mark
		const popupTrigger = document.createElement("span");
		popupTrigger.innerHTML = '<sup class=popup-symbol>?</sup>';
		popupTrigger.className = "popup-trigger";
		popupTrigger.style.cursor = "help";
		popupTrigger.style.marginLeft = "2pt";
		popupTrigger.style.color = 'lightgray'

		// create grade
		const grade = document.createElement("span");
		grade.innerHTML = points2grade[average_rating]
		grade.style.fontWeight = "bold"


		const margin_ratings = document.createElement("span")
		margin_ratings.className = "marginnote";
		const metalines = [];

		for (let key of Object.keys(book.ratings)) {
			metalines.push(metaLine(key, points2grade[book.ratings[key]]));
		}

		margin_ratings.innerHTML = metalines.join("");

		const rating_p = document.createElement("p");
		rating_p.appendChild(margin_ratings);
		rating_p.appendChild(document.createTextNode(`On ${review_date_string}, the ${club.name} graded`));
		rating_p.appendChild(popupTrigger);
		rating_p.appendChild(document.createTextNode(` ${book.meta.title} with a `));
		rating_p.appendChild(grade);
		rating_p.appendChild(document.createTextNode(`.`));
		section.appendChild(rating_p);




		// rating_p.appendChild(popupTrigger);

		// Popup hover behavior
		popupTrigger.addEventListener("mouseenter", () => {
			const spacing = 6;

			// Make popup visible but hidden so size can be measured
			gradingPopup.style.visibility = "hidden";
			gradingPopup.style.display = "block";

			const rect = popupTrigger.getBoundingClientRect();
			const popupRect = gradingPopup.getBoundingClientRect();

			let top = rect.bottom + spacing + window.scrollY; // default below
			let left = rect.left + window.scrollX;

			// If popup overflows bottom of viewport, place it above
			if (top + popupRect.height > window.scrollY + window.innerHeight) {
				top = rect.top - popupRect.height - spacing + window.scrollY;
			}

			// If popup overflows right edge, shift left
			if (left + popupRect.width > window.scrollX + window.innerWidth) {
				left = window.scrollX + window.innerWidth - popupRect.width - spacing;
			}

			if (left < window.scrollX) {
				left = window.scrollX + spacing;
			}

			gradingPopup.style.top = `${top}px`;
			gradingPopup.style.left = `${left}px`;

			// Now show it properly
			gradingPopup.style.visibility = "visible";
		});


		popupTrigger.addEventListener("mouseleave", () => {
			// delay hiding to allow moving into popup
			setTimeout(() => {
				if (!gradingPopup.matches(':hover')) {
					gradingPopup.style.display = "none";
				}
			}, 100);
		});

		gradingPopup.addEventListener("mouseleave", () => {
			gradingPopup.style.display = "none";
		});

	}

	if (reviews(book.reviews, book.meta.title)) {
		for (let key of Object.keys(book.reviews)) {
			if (book.reviews[key]) {
				const review_p = document.createElement("p")
				const reviewer = document.createElement("span")
				reviewer.textContent = key
				reviewer.style.fontWeight = "bold"
				reviewer.style.marginRight = "1em"
				review_p.append(reviewer)
				const review = document.createElement("span")
				review.textContent = book.reviews[key]
				review.style.fontStyle = "italic"
				review_p.append(review)
				section.appendChild(review_p)
			}
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


function ratings(ratings, title) {
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

function reviews(reviews, title) {
	// check for review object with content
	if (!reviews || Object.keys(reviews).length === 0) {
		console.warn(`No reviews found (${title}).`)
		return false; // no reviews, return null		
	}


	return true
}


function sortBooksByReviewDate(books) {
	return books.slice().sort((a, b) => {
		const dateA = new Date(a.review_date);
		const dateB = new Date(b.review_date);

		const timeA = isNaN(dateA.getTime()) ? -Infinity : dateA.getTime();
		const timeB = isNaN(dateB.getTime()) ? -Infinity : dateB.getTime();

		// Sort descending: latest dates first
		if (timeA === -Infinity && timeB === -Infinity) return 0;
		if (timeA === -Infinity) return 1; // invalid dates go last
		if (timeB === -Infinity) return -1;
		return timeB - timeA;
	});
}
