var removeIcon = " <i class='fa fa-times' aria-hidden='true'></i>";
var timer;
var $searchInput;
var $searchResults;

$(function() {
    // cache game search textbox and search results container div
    $searchInput = $("input[name='game_name']");
    $searchResults = $(".result-list");

    // add input listener to search texbox
    $searchInput.on("input", function() {
        // set timeout in order to throttle number of requests
        // timeout idea attributed to following StackOverflow answer:
        // http://stackoverflow.com/a/13209287
        clearTimeout(timer);
        timer = setTimeout(function() {
            // if search textbox is not empty
            if ($searchInput.val()) {
                // search for games matching input and show list
                search($searchInput.val());
                $searchResults.show();
            }
            // otherwise, if search textbox is empty
            else {
                // clear the list and hide it
                $searchResults.html("");
                $searchResults.hide();
            }
        }, 400);
    });
});

/*
 * Sends a request to the server for games matching query
 * and creates a list holding search results.
 *
 * @param {string} query - The user's input to be used for API.
 */
function search(query) {
    // display loading icon until the search is complete
    // http://www.ajaxload.info/
    showLoadingIcon();

    // send request to server for games matching user's input
    $.getJSON(Flask.url_for("search"), { q: query }, function(data) {
        // variable to hold list items for search results
        var results = [];
        // if no results were found, create a single list item displaying to the user as much
        if (data.length === 0) {
            results.push(createListItem(undefined));
        }
        // otherwise, for each result received from server,
        // create a list item and add it to results
        else {
            data.forEach(function(game) {
                results.push(createListItem(game));
            });
        }

        // display the result-list
        $searchResults.html(results);

        // add a click listener to list items provided results were found
        if (data.length !== 0) {
            $(".result-list li").on("click", function() {
                setGameSelection({
                    id: $(this).data("game-id"),
                    name: $(this).text(),
                    img: $("img", this).attr("src")
                });
            });
        }
    });
}

function showLoadingIcon() {
    $searchResults.html($("<li/>", {
        class: "list-group-item",
        html: $("<img/>", {
            class: "loading",
            src: "/static/img/ajax-loader.gif"
        })
    }));
}

/**
 * Creates a list item to a game search result and returns it.
 *
 * @param {Object} game - Game to create list for.
 * @return {Object} listItem - The created list item for game.
 */
function createListItem(game) {
    // if no results were found, return a list item specifying as much
    if (game === undefined) {
        return $("<li/>", {
            class: "list-group-item empty-list",
            text: "No games were found matching your input."
        });
    }

    // create the list item
    var listItem = $("<li/>", {
        class: "list-group-item",
        "data-game-id": game.id,
    });

    // some game covers were missing from API, so had to check
    // if it's missing in order to display a placeholder instead
    var img = {};
    if (game.cover) {
        img.src = game.cover.url;
    }
    else {
        img.src = "https://placeholdit.imgix.net/~text?txtsize=22&txt=Missing%20cover&w=90&h=90";
    }
    img.alt = game.name;

    var wrapper = $("<div/>", {
        class: "list-content-wrapper"
    });

    $("<img/>", {
        src: img.src,
        alt: img.alt
    }).appendTo(wrapper);

    wrapper.append(game.name);

    wrapper.appendTo(listItem);

    return listItem;
}

/**
 * Sets and displays a panel containing the selected game instead of
 * a search textbox.
 *
 * @param {Object} game - Selected game to display.
 */
function setGameSelection(game) {
    // clear the result list and hide it, since it's not needed anymore
    $searchResults.html("").hide();

    // set the value of search textbox to the name of the selected game
    // and hide it, will be used later for form submission (but the user doesn't need to see it)
    $("input[name='game_name']").val(game.name).hide();

    // show the panel that will hold the name of the selected game
    $(".game-panel").show();
    // set the panel body to hold the name of the game along with a remove icon
    // in order to enable users to clear the selection
    $(".game-panel .panel-body").html(game.name + removeIcon);

    // set additional hidden inputs which will be used by the server on form submission
    $("input[name='igdb_id']").val(game.id);
    $("input[name='image_url']").val(game.img);

    // set click listener for the remove icon to clear selection
    $(".game-panel .panel-body .fa-times").on("click", function() {
        clearGameSelection();
    });
}

/**
 * Clears a game selection and displays a search textbox instead.
 */
function clearGameSelection() {
    // clear the game selection from the panel since it's not needed anymore
    $(".game-panel .panel-body").html("");
    // hide the game panel and show the search textbox instead
    $(".game-panel").hide();
    $("input[name='game_name']").val("").show().focus();

    // clear the hidden fields
    $("input[name='igdb_id']").val("");
    $("input[name='image_url']").val("");
}
