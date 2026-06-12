import QtQuick
import QtQuick.Controls.Basic
import ".."

Drawer {
    id: control

    property string title: ""
    default property alias panel_content: contentColumn.data

    edge: Qt.RightEdge
    modal: true
    width: 420
    height: parent ? parent.height : 0
    padding: 0

    Overlay.modal: Rectangle {
        color: Qt.rgba(0, 0, 0, 0.3)
    }

    enter: Transition {
        NumberAnimation { property: "position"; duration: 200; easing.type: Easing.OutCubic }
    }

    exit: Transition {
        NumberAnimation { property: "position"; duration: 200; easing.type: Easing.InCubic }
    }

    background: Rectangle {
        color: Theme.surface

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.hairline_strong
        }
    }

    contentItem: Item {
        Item {
            id: headerArea
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 56

            Label {
                anchors.left: parent.left
                anchors.leftMargin: 20
                anchors.right: closeButton.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: control.title
                elide: Text.ElideRight
                color: Theme.text_primary
                font.pixelSize: 18
                font.weight: Font.Bold
                font.capitalization: Font.AllUppercase
                font.letterSpacing: 1.5
            }

            MilaButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                variant: "ghost"
                text: "✕"
                font.pixelSize: 18
                font.letterSpacing: 0
                leftPadding: 12
                rightPadding: 12
                onClicked: control.close()
            }
        }

        Rectangle {
            id: divider
            anchors.top: headerArea.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.hairline
        }

        Flickable {
            id: flick
            anchors.top: divider.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            contentWidth: flick.width
            contentHeight: contentColumn.height + 40
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: contentColumn
                x: 20
                y: 20
                width: flick.width - 40
                spacing: 12
            }

            ScrollBar.vertical: MilaScrollBar {}
        }
    }
}
