var removeIcon = " <i class='fa fa-times' aria-hidden='true'></i>";
var searchTimer;
var listTimer;
var $searchInput;
var $searchResults;

$(function() {
    // figure out on which page the user is, and set the 
    // corresponding navigation link to be the active one
    // http://totalprogus.blogspot.co.il/2013/12/bootstrap-add-active-class-to-li.html
    $("a[href='" + document.location.pathname + "']").parent().addClass("active");

    // cache game search textbox and search results container div
    $searchInput = $("input[name='game_name']");
    $searchResults = $(".result-list");

    // add input listener to search texbox
    $searchInput.on("input", function() {
        // set timeout in order to throttle number of requests
        // timeout idea attributed to following StackOverflow answer:
        // http://stackoverflow.com/a/13209287
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function() {
            // if search textbox is not empty
            if ($searchInput.val()) {
                // search for games matching input and show list
                search($searchInput.val());
                $searchResults.show();
            }
            // otherwise, if search textbox is empty
            else {
                // clear the list and hide it
                closeResultList();
            }
        }, 400);
    });

    // close search result list when user clicks outside
    // http://stackoverflow.com/a/7385673
    $(document).mouseup(function(event) {
        event.stopPropagation();
        var $resultItem = $(".result-item");
        if (!$resultItem.is(event.target) 
            && $resultItem.has(event.target).length === 0 
            && !$(".form-control").is(event.target)
            && !$("#game-form [type='submit']").is(event.target)) {
            closeResultList();
            $("input[name='game_name']").val("");
        }
    });

    // toggle between minus and plus signs as the user collapses/expands lists
    $(".panel-title a").on("click", function() {
        var title = this;
        clearTimeout(listTimer);
        // wait 300 milliseconds to sync in with the slide effect
        listTimer = setTimeout(function() {
            if ($(title).hasClass("collapsed")) {
                $("i", title).removeClass("fa-minus-square-o").addClass("fa-plus-square-o");
            }
            else {
                $("i", title).removeClass("fa-plus-square-o").addClass("fa-minus-square-o");
            }
        }, 300);
    });

    // display modal to confirm game/platform deletion
    $(".delete").on("click", function(event) {
        // stop form submission
        event.preventDefault();
        var $form = $(this).closest("form");
        // attempt to get game or platform name
        var game = $("input[name='entry_game']").val();
        var platform = $("input[name='platform_name']").val();
        // show either the game or platform name in the modal body, 
        // depending on context
        $(".modal-body span").text(game || platform);
        // display modal
        $(".modal").modal({
            keyboard: true
        })
        // submit form if user has confirmed
        .on("click", "#confirm", function() {
            $form.trigger("submit");
        });
    });

    // initialize tooltips
    $('[data-toggle="tooltip"]').tooltip({
        delay: {
            "show": 500
        },
        placement: "bottom"
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
        if (data.results.length === 0) {
            results.push(createListItem(undefined));
        }
        // otherwise, for each result received from server,
        // create a list item and add it to results
        else {
            data.results.forEach(function(game) {
                results.push(createListItem(game));
            });
        }

        // display the result-list
        $searchResults.html(results);

        // add a click listener to list items provided results were found
        if (data.results.length !== 0) {
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

/**
 * Displays a loading icon while waiting for response from server.
 */
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
            class: "list-group-item text-center",
            text: "No games were found matching your input."
        });
    }

    // create the list item
    var listItem = $("<li/>", {
        class: "list-group-item result-item",
        "data-game-id": game.id,
    });

    // some game covers were missing from API, so had to check
    // if it's missing in order to display a placeholder instead
    var img;
    if (game.cover) {
        img = game.cover.url;
    }
    else {
        img = "https://placeholdit.imgix.net/~text?txtsize=22&txt=Missing%20cover&w=90&h=90";
    }

    // create a wrapper for list content and append game data to it
    var wrapper = $("<div/>", {
        class: "list-content-wrapper"
    });
    $("<img/>", {
        src: img,
        alt: game.name
    }).appendTo(wrapper);
    wrapper.append(game.name);

    // append wrapper with game data to the created list item
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
    // close the search result list, since it's not needed anymore
    closeResultList();

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

/**
 * Closes the search result list.
 */
function closeResultList() {
    // clear the result list and hide it
    $searchResults.html("").hide();
}
