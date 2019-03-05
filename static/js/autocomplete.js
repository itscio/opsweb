(function($) {
    $.input_host = function(target, data, itemSelectFunction) {
    		var defaulOption = {
    			suggestMaxHeight: '200px',//弹出框最大高度
    			itemColor : '#000000',//默认字体颜色
    			itemBackgroundColor:'white',//默认背景颜色
    			itemOverColor : 'blue',//选中字体颜色
    			itemOverBackgroundColor : 'white',//选中背景颜色
    			itemPadding : 3 ,//item间距
    			fontSize : 14 ,//默认字体大小
    			alwaysShowALL : true //点击input是否展示所有可选项
    			};
        var maxFontNumber = 0;//最大字数
        var currentItem;
        var suggestContainerId = target + "-suggest";
        var suggestContainerWidth = $('#' + target).innerWidth();
        var suggestContainerLeft = $('#' + target).offset().left;
        var suggestContainerTop = $('#' + target).offset().top + $('#' + target).outerHeight();

        var showClickTextFunction = function() {
            $('#' + target).val(this.innerText);
            currentItem = null;
            $('#' + suggestContainerId).hide();
        }
        var suggestContainer;
        if ($('#' + suggestContainerId)[0]) {
            suggestContainer = $('#' + suggestContainerId);
            suggestContainer.empty();
        } else {
            suggestContainer = $('<div></div>'); //创建一个子<div>
        }

        suggestContainer.attr('id', suggestContainerId);
        suggestContainer.attr('tabindex', '0');
        suggestContainer.hide();
        var _initItems = function(items) {
            suggestContainer.empty();
            for (var i = 0; i < items.length; i++) {
            		if(items[i].text.length > maxFontNumber){
            			maxFontNumber = items[i].text.length;
            			}
                var suggestItem = $('<div></div>'); //创建一个子<div>
                suggestItem.attr('id', items[i].id);
                suggestItem.append(items[i].text);
                suggestItem.css({
                		'padding':defaulOption.itemPadding + 'px',
                    'white-space':'nowrap',
                    'cursor': 'pointer',
                    'background-color': defaulOption.itemBackgroundColor,
                    'color': defaulOption.itemColor
                });
                suggestItem.bind("mouseover",
                function() {
                    $(this).css({
                        'background-color': defaulOption.itemOverBackgroundColor,
                        'color': defaulOption.itemOverColor
                    });
                    currentItem = $(this);
                });
                suggestItem.bind("mouseout",
                function() {
                    $(this).css({
                        'background-color': defaulOption.itemBackgroundColor,
                        'color': defaulOption.itemColor
                    });
                    currentItem = null;
                });
                suggestItem.bind("click", showClickTextFunction);
                suggestItem.bind("click", itemSelectFunction);
                suggestItem.appendTo(suggestContainer);
                suggestContainer.appendTo(document.body);
            }
        }

        var inputChange = function() {
            var inputValue = $('#' + target).val();
            inputValue = inputValue.replace(/[\-\[\]{}()*+?.,\\\^$|#\s]/g, "\\$&");
            var matcher = new RegExp(inputValue, "i");
            return $.grep(data,
            function(value) {
                return matcher.test(value.text);
            });
        }

        $('#' + target).bind("keyup",
        function() {
            _initItems(inputChange());
        });
        $('#' + target).bind("blur",
        function() {
        		if(!$('#' + suggestContainerId).is(":focus")){
        			$('#' + suggestContainerId).hide();
        			if (currentItem) {
                currentItem.trigger("click");
            	}
            	currentItem = null;
        			return;
        			}                       
        });

        $('#' + target).bind("click",
        function() {
            if (defaulOption.alwaysShowALL) {
                _initItems(data);
            } else {
                _initItems(inputChange());
            }
            $('#' + suggestContainerId).removeAttr("style");
            var containerWidth = Math.max(suggestContainerWidth);
            $('#' + suggestContainerId).css({
                'border': '1px solid #ccc',
                'max-height': '200px',
                'top': suggestContainerTop,
                'left': suggestContainerLeft,
                'width': containerWidth,
                'position': 'absolute',
                'font-size': defaulOption.fontSize+'px',
                'font-family':'Arial',
                'z-index': 99999,
                'background-color': '#FFFFFF',
                'overflow-y': 'auto',
                'overflow-x': 'hidden',
                'white-space':'nowrap'

            });
            $('#' + suggestContainerId).show();
        });
        _initItems(data);

        $('#' + suggestContainerId).bind("blur",
        function() {
            $('#' + suggestContainerId).hide();
        });

    }

    $.input_uri = function(target, data, itemSelectFunction) {
    		var defaulOption = {
    			suggestMaxHeight: '200px',//弹出框最大高度
    			itemColor : '#000000',//默认字体颜色
    			itemBackgroundColor:'white',//默认背景颜色
    			itemOverColor : 'blue',//选中字体颜色
    			itemOverBackgroundColor : 'white',//选中背景颜色
    			itemPadding : 3 ,//item间距
    			fontSize : 14 ,//默认字体大小
    			alwaysShowALL : true //点击input是否展示所有可选项
    			};
        var maxFontNumber = 0;//最大字数
        var currentItem;
        var suggestContainerId = target + "-suggest";
        var suggestContainerWidth = $('#' + target).innerWidth();
        var suggestContainerLeft = $('#' + target).offset().left;
        var suggestContainerTop = $('#' + target).offset().top + $('#' + target).outerHeight();

        var showClickTextFunction = function() {
            $('#' + target).val(this.innerText);
            currentItem = null;
            $('#' + suggestContainerId).hide();
            set_cookies(target);
        }
        var suggestContainer;
        if ($('#' + suggestContainerId)[0]) {
            suggestContainer = $('#' + suggestContainerId);
            suggestContainer.empty();
        } else {
            suggestContainer = $('<div></div>'); //创建一个子<div>
        }

        suggestContainer.attr('id', suggestContainerId);
        suggestContainer.attr('tabindex', '0');
        suggestContainer.hide();
        var _initItems = function(items) {
            suggestContainer.empty();
            for (var i = 0; i < items.length; i++) {
            		if(items[i].text.length > maxFontNumber){
            			maxFontNumber = items[i].text.length;
            			}
                var suggestItem = $('<div></div>'); //创建一个子<div>
                suggestItem.attr('id', items[i].id);
                suggestItem.append(items[i].text);
                suggestItem.css({
                		'padding':defaulOption.itemPadding + 'px',
                    'white-space':'nowrap',
                    'cursor': 'pointer',
                    'background-color': defaulOption.itemBackgroundColor,
                    'color': defaulOption.itemColor
                });
                suggestItem.bind("mouseover",
                function() {
                    $(this).css({
                        'background-color': defaulOption.itemOverBackgroundColor,
                        'color': defaulOption.itemOverColor
                    });
                    currentItem = $(this);
                });
                suggestItem.bind("mouseout",
                function() {
                    $(this).css({
                        'background-color': defaulOption.itemBackgroundColor,
                        'color': defaulOption.itemColor
                    });
                    currentItem = null;
                });
                suggestItem.bind("click", showClickTextFunction);
                suggestItem.bind("click", itemSelectFunction);
                suggestItem.appendTo(suggestContainer);
                suggestContainer.appendTo(document.body);
            }
        }

        var inputChange = function() {
            var inputValue = $('#' + target).val();
            inputValue = inputValue.replace(/[\-\[\]{}()*+?.,\\\^$|#\s]/g, "\\$&");
            var matcher = new RegExp(inputValue, "i");
            return $.grep(data,
            function(value) {
                return matcher.test(value.text);
            });
        }

        $('#' + target).bind("keyup",
        function() {
            _initItems(inputChange());
        });
        $('#' + target).bind("blur",
        function() {
        		if(!$('#' + suggestContainerId).is(":focus")){
        			$('#' + suggestContainerId).hide();
        			if (currentItem) {
                currentItem.trigger("click");
            	}
            	currentItem = null;
        			return;
        			}
        });

        $('#' + target).bind("click",
        function() {
            if (defaulOption.alwaysShowALL) {
                _initItems(data);
            } else {
                _initItems(inputChange());
            }
            $('#' + suggestContainerId).removeAttr("style");
            $('#' + suggestContainerId).css({
                'border': '1px solid #ccc',
                'max-height': '200px',
                'top': suggestContainerTop,
                'left': suggestContainerLeft,
                'width': 'auto',
                'position': 'absolute',
                'font-size': defaulOption.fontSize+'px',
                'font-family':'Arial',
                'z-index': 99999,
                'background-color': '#FFFFFF',
                'overflow-y': 'auto',
                'overflow-x': 'hidden',
                'white-space':'nowrap'

            });
            $('#' + suggestContainerId).show();
        });
        _initItems(data);

        $('#' + suggestContainerId).bind("blur",
        function() {
            $('#' + suggestContainerId).hide();
        });

    }
})(jQuery);
